"""Constants and schemas for the event system."""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from ..exceptions import EventError

# Channel definitions
CHANNELS = {
    "SYSTEM": "system",
    "TASK": "task",
    "STORY": "story",
    "DESIGN": "design",
    "TEST": "test",
    "FEEDBACK": "feedback",
    "DEPLOYMENT": "deployment"
}

class EventType(str, Enum):
    """Types of events in the system."""
    # Task events
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    
    # Story events
    STORY_ASSIGNED = "story_assigned"
    STORY_COMPLETED = "story_completed"
    
    # Design events
    DESIGN_CREATED = "design_created"
    
    # Test events
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    
    # Feedback events
    FEEDBACK_RECEIVED = "feedback_received"
    
    # Deployment events
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"

class EventPriority(str, Enum):
    """Priority levels for events."""
    LOW = "low"           # Non-critical events that can be processed later
    MEDIUM = "medium"     # Default priority for most events
    HIGH = "high"         # Important events that should be processed soon
    CRITICAL = "critical" # Urgent events that require immediate attention

class EventStatus(str, Enum):
    """Status of events in the system."""
    PENDING = "pending"       # Event has been created but not yet processed
    PROCESSING = "processing" # Event is currently being processed
    COMPLETED = "completed"   # Event has been successfully processed
    FAILED = "failed"        # Event processing has failed

class CommunicationPattern(str, Enum):
    """Communication patterns supported by the event system."""
    PUBLISH_SUBSCRIBE = "pub_sub"   # One-to-many asynchronous communication
    REQUEST_RESPONSE = "req_resp"   # One-to-one synchronous communication
    BROADCAST = "broadcast"         # One-to-all communication

class EventSchema(BaseModel):
    """Schema for events in the system.
    
    Attributes:
        id: Unique identifier for the event
        type: Type of event
        channel: Channel the event is published to
        priority: Event priority level
        status: Current status of the event
        timestamp: When the event was created
        data: Event payload data
        correlation_id: ID to correlate related events
        reply_to: Channel to send responses to
        pattern: Communication pattern for this event
        service_name: Name of the service that created the event
    """
    id: str
    type: EventType
    channel: str
    priority: EventPriority = EventPriority.MEDIUM
    status: EventStatus = EventStatus.PENDING
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    pattern: CommunicationPattern = CommunicationPattern.PUBLISH_SUBSCRIBE
    service_name: Optional[str] = None
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        } 