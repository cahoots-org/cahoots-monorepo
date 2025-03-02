"""Infrastructure package for event sourcing."""

from .client import (
    ConnectionError,
    EventClient,
    EventClientError,
    PublishError,
    SubscriptionError,
    get_event_client,
)

__all__ = [
    "EventClient",
    "EventClientError",
    "ConnectionError",
    "PublishError",
    "SubscriptionError",
    "get_event_client",
]
