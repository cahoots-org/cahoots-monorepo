"""Event system package for Cahoots."""

from .config import EventConfig
from .exceptions import (
    EventError,
    EventHandlingError,
    EventPublishError,
    EventSizeLimitExceeded,
    EventSubscriptionError,
    EventValidationError,
)
from .infrastructure.client import (
    ConnectionError,
    EventClient,
    EventClientError,
    PublishError,
    SubscriptionError,
    get_event_client,
)
from .models import ContextEvent, Event, EventStatus

__all__ = [
    # Models
    "Event",
    "EventStatus",
    "ContextEvent",
    # Infrastructure
    "EventClient",
    "EventClientError",
    "ConnectionError",
    "PublishError",
    "SubscriptionError",
    "get_event_client",
    # Exceptions
    "EventError",
    "EventPublishError",
    "EventSubscriptionError",
    "EventHandlingError",
    "EventValidationError",
    "EventSizeLimitExceeded",
    # Config
    "EventConfig",
]
