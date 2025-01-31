"""Event system package for Cahoots."""
from .models import Event, EventStatus, ContextEvent
from .infrastructure.client import (
    EventClient,
    EventClientError,
    ConnectionError,
    PublishError,
    SubscriptionError,
    get_event_client
)
from .exceptions import (
    EventError,
    EventPublishError,
    EventSubscriptionError,
    EventHandlingError,
    EventValidationError,
    EventSizeLimitExceeded
)
from .config import EventConfig

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
    "EventConfig"
]
