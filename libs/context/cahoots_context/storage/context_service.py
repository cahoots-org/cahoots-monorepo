"""Context event service for managing project context."""
from datetime import datetime
from typing import Dict, List, Optional
import json
from uuid import UUID, uuid4
import sys
from asyncio import Lock
import logging
from sqlalchemy import Column

from cahoots_core.utils.infrastructure.database.client import get_db_client
from cahoots_core.utils.infrastructure.redis.client import get_redis_client
from cahoots_core.utils.version_vector import VersionVector
from fastapi import HTTPException

from cahoots_core.models.project import Project
from cahoots_events.models.events import ContextEventModel
from cahoots_core.utils.caching import CacheManager
from cahoots_core.exceptions import ValidationError, StorageError, ContextLimitError
from cahoots_core.exceptions import CahootsError
from cahoots_core.exceptions.base import ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)

class ContextEventService:
    """Service for managing context events with memory protection."""
    
    MAX_ITEMS = 100
    MAX_SIZE_BYTES = 1024 * 1024  # 1MB limit per context section
    
    def __init__(self):
        self.db = get_db_client()
        self.redis = get_redis_client()
        self.cache_manager = CacheManager(self.redis)
        self._init_locks = {}  # Per-context initialization locks
        
    def _get_context_lock(self, context_id: str) -> Lock:
        """Get or create a lock for a specific context."""
        if context_id not in self._init_locks:
            self._init_locks[context_id] = Lock()
        return self._init_locks[context_id]
        
    def _check_memory_limit(self, data: Dict) -> None:
        """Check if data exceeds memory limits."""
        size = len(json.dumps(data))
        if size > self.MAX_SIZE_BYTES:
            raise ContextLimitError(
                message=f"Data size {size} exceeds limit {self.MAX_SIZE_BYTES}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.RESOURCE_LIMIT
            )
            
    def _ensure_initialized(self, context: Dict, key: str) -> None:
        """Ensure context has required key initialized."""
        if key not in context:
            context[key] = []
        if len(context[key]) >= self.MAX_ITEMS:
            raise ContextLimitError(
                message=f"{key} exceed limit {self.MAX_ITEMS}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.RESOURCE_LIMIT
            )
    
    async def _ensure_initialized(self, context: Dict, key: str, factory=list) -> None:
        """Safely initialize a context key if not present."""
        if key not in context:
            async with self._get_context_lock(str(id(context))):
                if key not in context:  # Double-check after lock
                    context[key] = factory()
    
    async def apply_code_change(self, context: Dict, event_data: Dict) -> None:
        """Apply a code change event to the context."""
        self._check_memory_limit(event_data)
        await self._ensure_initialized(context, "code_changes")
        
        context["code_changes"].append(event_data)
        if len(context["code_changes"]) > self.MAX_ITEMS:
            # Keep only the most recent items up to the limit
            context["code_changes"] = sorted(
                context["code_changes"],
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:self.MAX_ITEMS]

    async def apply_architectural_decision(self, context: Dict, event_data: Dict) -> None:
        """Apply an architectural decision event to the context."""
        self._check_memory_limit(event_data)
        await self._ensure_initialized(context, "architectural_decisions")
        
        if len(context["architectural_decisions"]) >= self.MAX_ITEMS:
            raise ContextLimitError(
                message=f"Architectural decisions exceed limit {self.MAX_ITEMS}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.RESOURCE_LIMIT
            )
            
        context["architectural_decisions"].append(event_data)

    async def apply_standard_update(self, context: Dict, event_data: Dict) -> None:
        """Apply a standard update event to the context."""
        self._check_memory_limit(event_data)
        await self._ensure_initialized(context, "standards", dict)
        
        # Clean update to prevent memory leaks
        context["standards"] = event_data.copy()

    async def apply_event_to_context(self, context: Dict, event: ContextEventModel) -> Dict:
        """Apply a single event to a context state."""
        # Deep copy context to prevent mutations
        new_context = json.loads(json.dumps(context))
        
        # Apply event based on type
        if event.event_type == "code_change":
            await self.apply_code_change(new_context, event.event_data)
        elif event.event_type == "architectural_decision":
            await self.apply_architectural_decision(new_context, event.event_data)
        elif event.event_type == "standard_update":
            await self.apply_standard_update(new_context, event.event_data)
        
        return new_context

    async def invalidate_caches(self, project_id: UUID) -> None:
        """Invalidate all caches related to a project."""
        cache_keys = [
            f"context:{project_id}",
            f"vector:{project_id}"
        ]
        
        for key in cache_keys:
            await self.cache_manager.delete(key)

    async def get_context(self, project_id: UUID) -> Dict:
        """Get the current context for a project, using cache when possible."""
        # Try to get from cache first
        cache_key = f"context:{project_id}"
        cached_context = await self.cache_manager.get(cache_key)
        if cached_context is not None:
            return cached_context

        # Build context from event store
        events = self.db.query(ContextEventModel)\
            .filter(ContextEventModel.project_id == str(project_id))\
            .order_by(ContextEventModel.timestamp.asc())\
            .all()
            
        if not events:
            # Only verify project exists if no events found
            project = self.db.query(Project).filter(Column("id") == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return {}
            
        context = await self.build_context_from_events(events)
        
        # Cache the result
        await self.cache_manager.set(cache_key, context)
        return context

    async def get_version_vector(self, project_id: UUID) -> VersionVector:
        """
        Get the current version vector for a project.
        """
        # Try to get from cache first
        cache_key = f"vector:get_version_vector:{project_id}"
        cached_vector = await self.cache_manager.get(cache_key, value_type=VersionVector)
        if cached_vector is not None:
            return cached_vector

        # Get latest event
        latest_event = self.db.query(ContextEventModel)\
            .filter(ContextEventModel.project_id == str(project_id))\
            .order_by(ContextEventModel.timestamp.desc())\
            .first()
            
        vector = VersionVector.new() if not latest_event else \
                 VersionVector(versions=latest_event.version_vector)
                 
        # Cache the result
        await self.cache_manager.set(cache_key, vector)
        return vector

    async def append_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: Dict,
        version_vector: Optional[VersionVector] = None
    ) -> ContextEventModel:
        """
        Append a new event to the project's context history with optimistic concurrency control.
        """
        # Verify project exists
        project = self.db.query(Project).filter(Column("id") == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # If version vector provided, verify it matches current state
        if version_vector:
            current_vector = await self.get_version_vector(project_id)
            if not current_vector.compatible_with(version_vector):
                raise HTTPException(status_code=409, detail="Version conflict detected")
            # Merge and increment the vector
            current_vector.merge(version_vector)
            current_vector.increment()
        else:
            # Get current vector and increment
            current_vector = await self.get_version_vector(project_id)
            current_vector.increment()

        # Create and store new event
        event = ContextEventModel(
            id=str(uuid4()),
            project_id=str(project_id),
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.utcnow(),
            version_vector=current_vector.versions
        )
        self.db.add(event)
        self.db.commit()
        
        # Invalidate caches
        await self.invalidate_caches(project_id)
        
        return event

    async def build_context_from_events(self, events: List[ContextEventModel]) -> Dict:
        """Build a complete context state from a sequence of events."""
        context = {}
        for event in events:
            context = await self.apply_event_to_context(context, event)
        return context
        