"""Event types and models for the event system."""
from enum import Enum
from typing import Any, Dict, Optional, Union, Tuple
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

class EventType(Enum):
    """Event types with versioning support."""
    # Task events
    TASK_CREATED = ("task.created", 1)
    TASK_UPDATED = ("task.updated", 1)
    TASK_DELETED = ("task.deleted", 1)
    TASK_ASSIGNED = ("task.assigned", 1)
    TASK_COMPLETED = ("task.completed", 1)
    
    # User events
    USER_CREATED = ("user.created", 1)
    USER_UPDATED = ("user.updated", 1)
    USER_DELETED = ("user.deleted", 1)
    
    # System events
    SYSTEM_ERROR = ("system.error", 1)
    SYSTEM_WARNING = ("system.warning", 1)
    SYSTEM_INFO = ("system.info", 1)
    
    # Service events
    SERVICE_STARTED = ("service.started", 1)
    SERVICE_STOPPED = ("service.stopped", 1)
    SERVICE_ERROR = ("service.error", 1)
    
    def __init__(self, event_name: str, version: int):
        """Initialize event type with name and version."""
        self.event_name = event_name
        self.version = version
    
    @property
    def full_name(self) -> str:
        """Get the full event name including version."""
        return f"{self.event_name}.v{self.version}"
    
    @classmethod
    def from_string(cls, event_str: str) -> "EventType":
        """Create EventType from string representation."""
        for event_type in cls:
            if event_type.event_name == event_str:
                return event_type
        raise ValueError(f"Invalid event type: {event_str}")

class EventPriority(Enum):
    """Event priority levels with numeric values."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    
    @property
    def description(self) -> str:
        """Get human-readable description of priority level."""
        return {
            self.LOW: "Low priority, non-urgent processing",
            self.NORMAL: "Normal priority, standard processing",
            self.HIGH: "High priority, expedited processing",
            self.CRITICAL: "Critical priority, immediate processing"
        }[self]

class EventStatus(Enum):
    """Event processing status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    
    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (no further processing expected)."""
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED}
    
    @property
    def is_active(self) -> bool:
        """Check if status indicates active processing."""
        return self in {self.PROCESSING, self.RETRYING}

class CommunicationPattern(Enum):
    """Communication patterns for event distribution."""
    BROADCAST = "broadcast"  # One-to-many distribution
    DIRECT = "direct"       # One-to-one delivery
    REQUEST = "request"     # Request expecting response
    RESPONSE = "response"   # Response to request
    
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
        event_id: Optional[UUID] = None
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
            "original_error": str(self.original_error) if self.original_error else None
        }

class EventSchema(BaseModel):
    """Schema for events in the system."""
    event_type: EventType
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[Union[str, EventError]] = None
    pattern: CommunicationPattern = Field(default=CommunicationPattern.BROADCAST)
    source: Optional[str] = None
    target: Optional[str] = None
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: Optional[UUID] = None
    reply_to: Optional[str] = None
    priority: EventPriority = Field(default=EventPriority.NORMAL)
    status: EventStatus = Field(default=EventStatus.PENDING)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
            UUID: str,
            EventType: lambda et: et.event_name,
            EventPriority: lambda ep: ep.value,
            EventStatus: lambda es: es.value,
            CommunicationPattern: lambda cp: cp.value
        }
    )
    
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
            priority=self.priority
        )

class EventContext:
    """Context for event correlation and tracking."""
    def __init__(
        self,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
        reply_to: Optional[str] = None
    ):
        """Initialize event context."""
        self.correlation_id = correlation_id or uuid4()
        self.causation_id = causation_id
        self.source = source
        self.target = target
        self.reply_to = reply_to
        self.timestamp = datetime.utcnow()
    
    def create_child_context(self, target: Optional[str] = None) -> "EventContext":
        """Create child context inheriting correlation."""
        return EventContext(
            correlation_id=self.correlation_id,
            causation_id=self.correlation_id,
            source=self.target or self.source,
            target=target,
            reply_to=self.reply_to
        )

class EventContext(BaseModel):
    """Event context information."""
    event_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PublishError(EventError):
    """Error during message publishing."""
    pass 