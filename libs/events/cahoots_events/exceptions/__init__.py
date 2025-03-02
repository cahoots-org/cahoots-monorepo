"""Event exceptions package."""

from .events import (
    EventError,
    EventHandlingError,
    EventPublishError,
    EventSizeLimitExceeded,
    EventSubscriptionError,
    EventValidationError,
)

__all__ = [
    "EventError",
    "EventPublishError",
    "EventSubscriptionError",
    "EventHandlingError",
    "EventValidationError",
    "EventSizeLimitExceeded",
]
