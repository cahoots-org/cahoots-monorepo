from datetime import datetime
from typing import Dict, List, Optional
import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from redis import Redis
from sqlalchemy.orm import Session

from src.database.models import Project, ContextEvent
from src.utils.redis_client import get_redis_client
from src.utils.version_vector import VersionVector
from src.utils.caching import CacheManager, cached

class ContextEventService:
    def __init__(self, db: Session, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis or get_redis_client()
        self.cache_manager = CacheManager(self.redis)
        
    @cached(ttl=3600, key_prefix="context")
    async def get_context(self, project_id: UUID) -> Dict:
        """
        Get the current context for a project, using cache when possible.
        """
        # Verify project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build context from event store
        events = self.db.query(ContextEvent)\
            .filter(ContextEvent.project_id == project_id)\
            .order_by(ContextEvent.timestamp.asc())\
            .all()
            
        context = self._build_context_from_events(events)
        return context

    @cached(ttl=3600, key_prefix="vector")
    async def get_version_vector(self, project_id: UUID) -> VersionVector:
        """
        Get the current version vector for a project.
        """
        # Get latest event
        latest_event = self.db.query(ContextEvent)\
            .filter(ContextEvent.project_id == project_id)\
            .order_by(ContextEvent.timestamp.desc())\
            .first()
            
        vector = VersionVector.new() if not latest_event else \
                 VersionVector.from_event(latest_event)
                 
        return vector

    async def append_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: Dict,
        version_vector: Optional[VersionVector] = None
    ) -> ContextEvent:
        """
        Append a new event to the project's context history with optimistic concurrency control.
        """
        # Verify project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # If version vector provided, verify it matches current state
        if version_vector:
            current_vector = await self.get_version_vector(project_id)
            if not current_vector.compatible_with(version_vector):
                raise HTTPException(status_code=409, detail="Version conflict detected")

        # Create and store new event
        event = ContextEvent(
            id=uuid4(),
            project_id=project_id,
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.utcnow()
        )
        self.db.add(event)
        self.db.commit()

        # Invalidate caches
        await self._invalidate_caches(project_id)
        
        return event

    async def _invalidate_caches(self, project_id: UUID) -> None:
        """Invalidate all caches related to a project."""
        cache_keys = [
            f"context:{project_id}",
            f"vector:{project_id}"
        ]
        
        for key in cache_keys:
            await self.cache_manager.delete(key)

    def _build_context_from_events(self, events: List[ContextEvent]) -> Dict:
        """
        Build a complete context state from a sequence of events.
        """
        context = {}
        for event in events:
            context = self._apply_event_to_context(context, event)
        return context

    def _apply_event_to_context(self, context: Dict, event: ContextEvent) -> Dict:
        """
        Apply a single event to a context state.
        """
        # Deep copy context to prevent mutations
        new_context = json.loads(json.dumps(context))
        
        # Apply event based on type
        if event.event_type == "code_change":
            self._apply_code_change(new_context, event.event_data)
        elif event.event_type == "architectural_decision":
            self._apply_architectural_decision(new_context, event.event_data)
        elif event.event_type == "standard_update":
            self._apply_standard_update(new_context, event.event_data)
        # Add more event types as needed
        
        return new_context

    def _apply_code_change(self, context: Dict, event_data: Dict) -> None:
        """
        Apply a code change event to the context.
        """
        if "code_changes" not in context:
            context["code_changes"] = []
        context["code_changes"].append(event_data)
        # Maintain a reasonable history size
        if len(context["code_changes"]) > 100:
            context["code_changes"] = context["code_changes"][-100:]

    def _apply_architectural_decision(self, context: Dict, event_data: Dict) -> None:
        """
        Apply an architectural decision event to the context.
        """
        if "architectural_decisions" not in context:
            context["architectural_decisions"] = []
        context["architectural_decisions"].append(event_data)

    def _apply_standard_update(self, context: Dict, event_data: Dict) -> None:
        """
        Apply a standard update event to the context.
        """
        if "standards" not in context:
            context["standards"] = {}
        context["standards"].update(event_data) 