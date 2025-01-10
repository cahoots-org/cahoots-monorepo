"""Constants and schemas for the event system."""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

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
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    STORY_ASSIGNED = "story_assigned"
    STORY_COMPLETED = "story_completed"
    DESIGN_CREATED = "design_created"
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    FEEDBACK_RECEIVED = "feedback_received"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"

class EventPriority(str, Enum):
    """Priority levels for events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventStatus(str, Enum):
    """Status of events in the system."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class CommunicationPattern(str, Enum):
    """Communication patterns supported by the event system."""
    PUBLISH_SUBSCRIBE = "pub_sub"
    REQUEST_RESPONSE = "req_resp"
    BROADCAST = "broadcast"

class EventError(Exception):
    """Base exception for event-related errors."""
    pass

class EventSchema(BaseModel):
    """Schema for events in the system."""
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