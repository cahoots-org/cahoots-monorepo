"""Event service for managing event lifecycle and retention."""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import sys
import json
import logging

from cahoots_core.exceptions.base import ErrorCategory, ErrorSeverity
from cahoots_events.exceptions.events import EventSizeLimitExceeded
from cahoots_events.bus.types import EventStatus
from cahoots_events.config import EventConfig
from redis import Redis
from fastapi import HTTPException

from cahoots_core.exceptions import StorageError, ValidationError
from cahoots_core.models.db_models import Project
from cahoots_events.models import Event
from cahoots_service.schemas.events import EventCreate, EventResponse
from cahoots_service.api.dependencies import ServiceDeps

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class EventService:
    """Service for managing events with retention policies."""
    
    MAX_EVENT_SIZE_BYTES = 1024 * 1024  # 1MB limit per event
    CLEANUP_LOCK_KEY = "event_cleanup_lock"
    LOCK_TIMEOUT = 60  # seconds
    
    def __init__(
        self,
        config: EventConfig,
        redis: Redis,
        db: Any
    ):
        """Initialize event service."""
        self.config = config
        self.redis = redis
        self.db = db
        self.cleanup_lock = asyncio.Lock()
        self.MAX_EVENT_SIZE_BYTES = config.max_event_size
        self.cleanup_task = None
        
    def _check_event_size(self, event: Event) -> None:
        """Check if event size exceeds limit."""
        event_size = len(event.model_dump_json().encode())
        if event_size > self.MAX_EVENT_SIZE_BYTES:
            raise EventSizeLimitExceeded(
                message=f"Event size {event_size} bytes exceeds limit of {self.MAX_EVENT_SIZE_BYTES} bytes",
                size=event_size,
                limit=self.MAX_EVENT_SIZE_BYTES
            )
            
    async def _acquire_cleanup_lock(self) -> bool:
        """Acquire distributed lock for cleanup."""
        return await self.redis.set(
            self.CLEANUP_LOCK_KEY,
            "1",
            ex=self.LOCK_TIMEOUT,
            nx=True
        )
        
    async def _release_cleanup_lock(self) -> None:
        """Release distributed cleanup lock."""
        await self.redis.delete(self.CLEANUP_LOCK_KEY)
        
    async def save_event(self, event: Event) -> None:
        """Save event to database and cache."""
        try:
            self._check_event_size(event)
            
            # Save to database
            await self.db.add(event)
            
            # Cache event with TTL
            event_json = event.model_dump_json()
            await self.redis.setex(
                f"event:{event.id}",
                self.config.cache_ttl_seconds,
                event_json
            )
        except EventSizeLimitExceeded as e:
            raise e
        except Exception as e:
            raise StorageError(
                message=f"Failed to save event: {str(e)}",
                operation="save_event",
                details={"event_id": str(event.id)}
            )
        
    async def get_event(self, event_id: UUID) -> Optional[Event]:
        """Get event by ID with cache."""
        # Try cache first
        cache_key = f"event:{event_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return Event.parse_raw(cached)
        
        # Fallback to database
        event = await self.db.get_event(event_id)
        if event:
            # Update cache
            event_json = event.model_dump_json()
            await self.redis.setex(
                cache_key,
                self.config.cache_ttl_seconds,
                event_json
            )
        return event
        
    async def get_project_events(
        self,
        project_id: UUID,
        status: Optional[EventStatus] = None
    ) -> List[Event]:
        """Get all events for a project."""
        events = await self.db.get_project_events(project_id)
        if status:
            events = [e for e in events if e.status == status]
        return events
            
    async def cleanup_expired_events(self) -> None:
        """Clean up expired events."""
        try:
            async with self.cleanup_lock:
                cutoff = datetime.utcnow() - timedelta(hours=self.config.retention_hours)
                events = await self.db.get_project_events(None)  # Get all events
                expired_events = [e for e in events if e.created_at <= cutoff]

                for event in expired_events:
                    await self.db.delete(event)
                    await self.clear_cache(event.id)
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")

    async def retry_failed_events(self) -> None:
        """Retry failed events that haven't exceeded retry limit."""
        events = await self.db.get_project_events(None)  # Get all events
        failed_events = [
            e for e in events 
            if e.status == EventStatus.FAILED and e.retry_count < self.config.max_retry_count
        ]

        for event in failed_events:
            # Create a new event with updated status and retry count
            updated_event = Event(
                id=event.id,
                project_id=event.project_id,
                type=event.type,
                status=EventStatus.PENDING,
                retry_count=event.retry_count + 1,
                priority=event.priority,
                data=event.data,
                created_at=event.created_at,
                updated_at=datetime.utcnow()
            )
            await self.save_event(updated_event)
        
    async def clear_cache(self, event_id: UUID) -> None:
        """Clear cached event."""
        await self.redis.delete(f"event:{event_id}") 