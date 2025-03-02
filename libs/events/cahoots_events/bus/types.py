"""Event types and models for the event system."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..types import BaseEvent, EventPriority, EventStatus, EventType


class CommunicationPattern(Enum):
    """Communication patterns for event distribution."""

    BROADCAST = "broadcast"  # One-to-many distribution
    DIRECT = "direct"  # One-to-one delivery
    REQUEST = "request"  # Request expecting response
    RESPONSE = "response"  # Response to request

    @property
    def requires_target(self) -> bool:
        """Check if pattern requires target specification."""
        return self in {self.DIRECT, self.REQUEST, self.RESPONSE}

    @property
    def expects_response(self) -> bool:
        """Check if pattern expects a response."""
        return self == self.REQUEST


class EventError(Exception):
    """Event processing error with context."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        event_type: Optional[EventType] = None,
        event_id: Optional[UUID] = None,
    ):
        """Initialize event error with context."""
        super().__init__(message)
        self.original_error = original_error
        self.event_type = event_type
        self.event_id = event_id
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "message": str(self),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.event_name if self.event_type else None,
            "event_id": str(self.event_id) if self.event_id else None,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class EventSchema(BaseEvent):
    """Schema for events in the bus system."""

    pattern: CommunicationPattern = CommunicationPattern.BROADCAST
    reply_to: Optional[str] = None
    service_name: Optional[str] = None

    def validate_pattern(self) -> None:
        """Validate pattern-specific requirements."""
        if self.pattern.requires_target and not self.target:
            raise ValueError(f"Pattern {self.pattern} requires target specification")
        if self.pattern == CommunicationPattern.RESPONSE and not self.correlation_id:
            raise ValueError("Response events must have correlation_id")

    def create_response(self, response_data: Dict[str, Any]) -> "EventSchema":
        """Create response event for request."""
        if self.pattern != CommunicationPattern.REQUEST:
            raise ValueError("Can only create response for REQUEST events")

        return EventSchema(
            event_type=self.event_type,
            event_data=response_data,
            pattern=CommunicationPattern.RESPONSE,
            source=self.target,
            target=self.source,
            correlation_id=self.correlation_id,
            causation_id=self.correlation_id,
            priority=self.priority,
        )


class EventContext(BaseModel):
    """Event context information."""

    event_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PublishError(EventError):
    """Error during message publishing."""

    pass
