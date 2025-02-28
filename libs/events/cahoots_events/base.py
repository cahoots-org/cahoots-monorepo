"""Base event classes and utilities"""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID, uuid4


@dataclass
class EventMetadata:
    """Metadata for events"""
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class Event(ABC):
    """Abstract base class for all events"""
    def __init__(self, event_id: UUID, timestamp: Any, metadata: Optional[EventMetadata] = None):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata or EventMetadata()
        self.validate()

    def validate(self):
        """Base validation method that can be extended by specific event types"""
        if not isinstance(self.event_id, UUID):
            raise ValueError("event_id must be a UUID")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")

    def with_context(self, **kwargs) -> 'Event':
        """Add context to the event"""
        self.metadata.context.update(kwargs)
        return self

    def caused_by(self, event: 'Event') -> 'Event':
        """Set the causation ID from another event"""
        self.metadata.causation_id = event.event_id
        self.metadata.correlation_id = event.metadata.correlation_id
        return self

    def triggered_by(self, actor_id: UUID) -> 'Event':
        """Set the actor who triggered this event"""
        self.metadata.actor_id = actor_id
        return self

    @property
    def version(self) -> int:
        """Get the schema version of this event"""
        return self.metadata.schema_version

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement aggregate_id") 