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
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis import Redis
from fastapi import HTTPException

from cahoots_core.exceptions import StorageError, ValidationError
from cahoots_core.models.project import Project
from cahoots_events.models import Event

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
        db: Session
    ):
        """Initialize event service."""
        self.config = config
        self.redis = redis
        self.db = db
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
        
    async def save_event(self, event: Event, commit: bool = True) -> None:
        """Save event to database and cache."""
        try:
            self._check_event_size(event)
            
            # Save to database
            self.db.add(event)
            await self.db.execute()
            if commit:
                await self.db.commit()
            
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
        event = self.db.query(Event).filter(Event.id == event_id).first()
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
        query = self.db.query(Event).filter(Event.project_id == project_id)
        if status:
            query = query.filter(Event.status == status)
        return query.order_by(Event.created_at.asc()).all()
        
    async def get_active_events(self, project_id: UUID) -> List[Event]:
        """Get active (non-expired) events for a project."""
        cutoff = datetime.utcnow() - timedelta(hours=self.config.retention_hours)
        return self.db.query(Event)\
            .filter(Event.project_id == project_id)\
            .filter(Event.created_at > cutoff)\
            .all()
            
    async def cleanup_expired_events(self):
        """Clean up expired events from database and cache."""
        lock_acquired = False
        try:
            # Acquire lock with timeout
            lock_acquired = await self.redis.set(
                "cleanup_lock", "1",
                ex=60,
                nx=True
            )
            
            if not lock_acquired:
                logger.info("Cleanup already in progress, skipping")
                return
            
            # Calculate cutoff time
            cutoff = datetime.utcnow() - timedelta(hours=self.config.retention_hours)
            
            # Get expired events
            expired = self.db.query(Event).filter(
                Event.created_at < cutoff
            ).all()
            
            if expired:
                # Delete from DB
                for event in expired:
                    self.db.delete(event)
                
                # Commit changes
                await self.db.commit()
                logger.info(f"Deleted {len(expired)} expired events from database")
                
                # Clear from cache
                for event in expired:
                    await self.redis.delete(f"event:{event.id}")
                logger.info(f"Cleared {len(expired)} expired events from cache")
                
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            if lock_acquired:
                await self.db.rollback()
        finally:
            if lock_acquired:
                await self.redis.delete("cleanup_lock")
                
    async def enforce_storage_limits(self, project_id: UUID) -> None:
        """Enforce storage limits by cleaning low priority events."""
        # Get events sorted by priority
        events = self.db.query(Event)\
            .filter(Event.project_id == project_id)\
            .order_by(Event.priority.asc())\
            .all()
            
        if not events:
            return
            
        # Calculate total size
        total_size = sum(len(event.model_dump_json().encode()) for event in events)
        
        # Remove oldest low priority events until under limit
        while total_size > self.config.max_storage_bytes and events:
            event = events.pop(0)  # Remove oldest low priority event
            self.db.delete(event)
            await self.redis.delete(f"event:{event.id}")
            total_size -= len(event.model_dump_json().encode())
            
        await self.db.commit()
        
    async def retry_failed_events(self) -> None:
        """Retry failed events that haven't exceeded retry limit."""
        failed_events = self.db.query(Event)\
            .filter(Event.status == EventStatus.FAILED)\
            .filter(Event.retry_count < self.config.max_retry_count)\
            .all()
            
        for event in failed_events:
            event.status = EventStatus.PENDING
            event.retry_count += 1
            
        await self.db.commit()
        
    async def clear_cache(self) -> None:
        """Clear all cached events."""
        pattern = "event:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
            
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        while True:
            try:
                await self.cleanup_expired_events()
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(self.config.processing_interval * 60) 