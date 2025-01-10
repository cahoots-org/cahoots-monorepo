"""Common event types and models."""
from enum import Enum
from typing import Any, Dict, Optional, Union
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class EventType(Enum):
    """Event types with versioning."""
    TASK_CREATED = ("task.created", 1)
    TASK_UPDATED = ("task.updated", 1)
    TASK_DELETED = ("task.deleted", 1)
    USER_CREATED = ("user.created", 1)
    SYSTEM_ERROR = ("system.error", 1)
    
    def __init__(self, event_name: str, version: int):
        self.event_name = event_name
        self.version = version

class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class EventStatus(Enum):
    """Event status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CommunicationPattern(Enum):
    """Communication patterns for events."""
    BROADCAST = "broadcast"  # One-to-many
    DIRECT = "direct"       # One-to-one
    REQUEST = "request"     # Request-response
    RESPONSE = "response"   # Response to request

class EventError(Exception):
    """Event processing error."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class EventSchema(BaseModel):
    """Schema for events in the system."""
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[Union[str, EventError]] = None
    pattern: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    reply_to: Optional[str] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

class EventContext:
    """Context for event correlation."""
    def __init__(
        self,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ):
        self.correlation_id = correlation_id or uuid4()
        self.causation_id = causation_id 