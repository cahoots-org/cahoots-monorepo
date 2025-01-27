"""Common types and enums for the event system."""
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

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
    RETRYING = "retrying"

class BaseEvent(BaseModel):
    """Base event model with common fields."""
    id: str
    type: EventType
    status: EventStatus = EventStatus.PENDING
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None 