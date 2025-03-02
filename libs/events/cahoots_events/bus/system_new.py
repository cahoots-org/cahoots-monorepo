"""Event system implementation."""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from redis.asyncio import Redis

from cahoots_core.utils.infrastructure.redis.client import get_redis_client

from ..exceptions import EventSizeLimitExceeded
from ..infrastructure.client import EventClient, EventClientError, SubscriptionError
from ..models import Event, EventStatus
from ..types import BaseEvent, EventPriority, EventType
from .queue import EventQueue
from .types import EventContext, EventError, EventSchema, PublishError

logger = logging.getLogger(__name__)


class EventSystemError(Exception):
    """Base exception for event system errors."""

    pass


class ConnectionError(EventSystemError):
    """Error indicating connection issues."""

    pass


class SubscriptionError(EventSystemError):
    """Error during channel subscription."""

    pass


class EventHandlingError(EventSystemError):
    """Error during event handling."""

    pass


class EventSystem:
    """Event system for handling event distribution."""

    def __init__(
        self,
        redis_client: Redis,
        dlq_prefix: str = "dlq:",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        heartbeat_interval: float = 5.0,
    ) -> None:
        """Initialize event system.

        Args:
            redis_client: Redis client instance
            dlq_prefix: Prefix for dead letter queue keys
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            heartbeat_interval: Interval for heartbeat checks
        """
        self.redis = redis_client
        self._pubsub_client = None
        self._pubsub = None
        self._connected = False
        self._handlers = defaultdict(list)
        self._filters = {}
        self._transforms = {}
        self.logger = logging.getLogger(__name__)
        self._dlq_prefix = dlq_prefix
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task = None

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        try:
            event_str = event.model_dump_json()
            await self.redis.publish(str(event.type), event_str)

            # Process handlers
            handlers = self._handlers.get(str(event.type), [])
            for handler in handlers:
                await self._handle_event(event, handler)
        except Exception as e:
            raise PublishError(f"Failed to publish event: {e}")

    async def get_handlers(self, event_type: str) -> List[Callable[[Event], Awaitable[None]]]:
        """Get all handlers for an event type.

        Args:
            event_type: Type of events to get handlers for

        Returns:
            List of handler functions
        """
        return self._handlers[event_type]

    async def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Awaitable[None]],
        filter_fn: Optional[Callable[[Event], bool]] = None,
        transform_fn: Optional[Callable[[Event], Event]] = None,
    ) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            handler: Async function to handle events
            filter_fn: Optional function to filter events
            transform_fn: Optional function to transform events before handling
        """
        if not self._connected:
            await self.connect()

        self._handlers[event_type].append(handler)
        if filter_fn:
            self._filters[handler] = filter_fn
        if transform_fn:
            self._transforms[handler] = transform_fn

    async def unsubscribe(
        self, event_type: str, handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Unsubscribe a handler from events.

        Args:
            event_type: Type of events to unsubscribe from
            handler: Handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            self._filters.pop(handler, None)
            self._transforms.pop(handler, None)

    async def _handle_event(
        self, event: Event, handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Handle a single event with a handler.

        Args:
            event: Event to handle
            handler: Handler function
        """
        try:
            if handler in self._filters:
                if not self._filters[handler](event):
                    return

            if handler in self._transforms:
                event = self._transforms[handler](event)

            await handler(event)
        except Exception as e:
            self.logger.error(f"Error in event handler: {e}")
            raise EventHandlingError(f"Handler failed: {e}")

    async def connect(self) -> None:
        """Connect to Redis and initialize pubsub client.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            if not self._connected:
                # Verify Redis connection
                await self.verify_connection()

                # Initialize pubsub
                self._pubsub_client = self.redis
                self._pubsub = await self._pubsub_client.pubsub()
                await self._pubsub.subscribe("__heartbeat__")

                # Start heartbeat task
                if not self._heartbeat_task:
                    self._heartbeat_task = asyncio.create_task(self._heartbeat())

                self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis and cleanup resources."""
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Cleanup pubsub
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
            self._pubsub = None

        if self._pubsub_client:
            await self._pubsub_client.aclose()
            self._pubsub_client = None

        self._connected = False

    async def verify_connection(self) -> bool:
        """Verify connection to Redis is active.

        Returns:
            bool: True if connected, False otherwise

        Raises:
            ConnectionError: If connection verification fails
        """
        try:
            await self.redis.ping()
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Redis connection failed: {e}") from e

    async def _heartbeat(self) -> None:
        """Send periodic heartbeat to verify connection."""
        while True:
            try:
                await self.verify_connection()
                await asyncio.sleep(self._heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Heartbeat failed: {e}")
                await asyncio.sleep(1)  # Short delay before retry
