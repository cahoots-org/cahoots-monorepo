"""Constants and schemas for the event system."""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from ..exceptions import EventError
from cahoots_events.bus.types import EventStatus, EventType, EventPriority

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
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    pattern: CommunicationPattern = CommunicationPattern.PUBLISH_SUBSCRIBE
    service_name: Optional[str] = None
    
    @property
    def model_serializer(self):
        """Custom serialization."""
        return {
            "timestamp": lambda dt: dt.isoformat() if dt else None
        } 