"""Event system package for asynchronous communication."""

from .constants import (
    CHANNELS,
    CommunicationPattern,
    EventError,
    EventPriority,
    EventSchema,
    EventStatus,
    EventType,
)
from .queue import EventQueue, Message, QueueError
from .system import (
    ConnectionError,
    EventSystem,
    EventSystemError,
    PublishError,
    SubscriptionError,
)
from .types import (
    CommunicationPattern,
    EventContext,
    EventError,
    EventPriority,
    EventSchema,
    EventStatus,
    EventType,
)

__all__ = [
    # Constants
    "CHANNELS",
    # Types
    "EventType",
    "EventPriority",
    "EventStatus",
    "CommunicationPattern",
    "EventError",
    "EventSchema",
    "EventContext",
    # System
    "EventSystem",
    "EventSystemError",
    "ConnectionError",
    "PublishError",
    "SubscriptionError",
    # Queue
    "Message",
    "EventQueue",
    "QueueError",
]
