"""Distributed event system implementation using Redis."""
from typing import Dict, Any, Optional, Callable, Awaitable, List
import json
import logging
import asyncio
from datetime import datetime
from uuid import uuid4
from redis.asyncio import Redis

from src.utils.event_constants import (
    EventSchema,
    EventType,
    EventPriority,
    EventStatus,
    EventError,
    CommunicationPattern,
    CHANNELS
)

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (EventType, EventPriority, EventStatus, CommunicationPattern)):
            return obj.value
        return super().default(obj)

class EventSystem:
    """Redis-based distributed event system implementation."""

    def __init__(self, redis: Redis, service_name: Optional[str] = None):
        """Initialize the distributed event system.
        
        Args:
            redis: Redis client instance
            service_name: Optional service name
        """
        self.redis = redis
        self._service_name = service_name
        self._connected = False
        self._handlers: Dict[str, List[Callable[[EventSchema], Awaitable[None]]]] = {}
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}

    @property
    def is_connected(self) -> bool:
        """Check if event system is connected."""
        return self._connected

    async def verify_connection(self) -> bool:
        """Verify Redis connection is active.
        
        Returns:
            bool: True if connection is active, False otherwise
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logging.error(f"Redis connection verification failed: {str(e)}")
            return False

    @property
    def service_name(self) -> Optional[str]:
        """Return the service name."""
        return self._service_name

    async def connect(self) -> None:
        """Connect to Redis and start listening for events."""
        try:
            await self.redis.ping()
            self._connected = True
        except Exception as e:
            logging.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            raise EventError("Failed to connect to Redis") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._connected = False
        
        # Cancel all pubsub tasks
        for task in self._pubsub_tasks.values():
            task.cancel()
        self._pubsub_tasks.clear()
        
        # Unsubscribe from all channels
        for channel in list(self._handlers.keys()):
            pubsub = self.redis.pubsub()
            pubsub.unsubscribe(channel)
        self._handlers.clear()

    async def publish(self, event: EventSchema) -> None:
        """Publish an event to Redis.
        
        Args:
            event: Event to publish
        """
        if not self.is_connected:
            raise EventError("Event system not connected")

        if not event.service_name:
            event.service_name = self.service_name

        try:
            event_data = event.model_dump()
            event_json = json.dumps(event_data, cls=DateTimeEncoder)
            await self.redis.publish(event.channel, event_json)
            await self.redis.set(
                f"event:{event.id}",
                event_json,
                ex=86400  # Store for 24 hours
            )
        except Exception as e:
            logging.error(f"Failed to publish event: {str(e)}")
            event.status = EventStatus.FAILED
            raise EventError(f"Failed to publish event: {str(e)}") from e

    async def subscribe(self, channel: str, handler: Callable[[EventSchema], Awaitable[None]]) -> None:
        """Subscribe to events on a channel.
        
        Args:
            channel: Channel to subscribe to
            handler: Event handler function
        """
        if not self.is_connected:
            raise EventError("Event system not connected")

        if channel not in self._handlers:
            self._handlers[channel] = []
            
            # Start Redis subscription
            pubsub = self.redis.pubsub()
            pubsub.subscribe(channel)
            
            # Start background task to process messages
            task = asyncio.create_task(self._process_messages(pubsub, channel))
            self._pubsub_tasks[channel] = task
            
        self._handlers[channel].append(handler)

    async def unsubscribe(self, channel: str, handler: Callable[[EventSchema], Awaitable[None]]) -> None:
        """Unsubscribe from events on a channel.
        
        Args:
            channel: Channel to unsubscribe from
            handler: Event handler function to remove
        """
        if channel in self._handlers:
            self._handlers[channel].remove(handler)
            if not self._handlers[channel]:
                del self._handlers[channel]
                pubsub = self.redis.pubsub()
                pubsub.unsubscribe(channel)
                
                # Cancel the pubsub task
                if channel in self._pubsub_tasks:
                    self._pubsub_tasks[channel].cancel()
                    del self._pubsub_tasks[channel]

    async def _process_messages(self, pubsub, channel: str) -> None:
        """Process messages from Redis subscription.
        
        Args:
            pubsub: Redis pubsub connection
            channel: Channel being processed
        """
        while True:
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message and channel in self._handlers:
                    event_data = json.loads(message["data"])
                    event = EventSchema(**event_data)
                    
                    for handler in self._handlers[channel]:
                        try:
                            await handler(event)
                        except Exception as e:
                            logging.error(f"Error in event handler: {str(e)}")
                            event.status = EventStatus.FAILED
                await asyncio.sleep(0.1)  # Avoid tight loop
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
                await asyncio.sleep(1)  # Longer sleep on error

    async def replay_events(self, channel: str) -> List[EventSchema]:
        """Replay events from a channel.
        
        Args:
            channel: Channel to replay events from
            
        Returns:
            List of events from the channel
        """
        if not self.is_connected:
            raise EventError("Event system not connected")

        try:
            # Get all events for channel from Redis
            keys = await self.redis.keys(f"event:*")
            events = []
            
            for key in keys:
                event_data = await self.redis.get(key)
                if event_data:
                    event = EventSchema(**json.loads(event_data))
                    if event.channel == channel:
                        events.append(event)
                        
            return sorted(events, key=lambda e: e.timestamp)
            
        except Exception as e:
            logging.error(f"Failed to replay events: {str(e)}")
            raise EventError(f"Failed to replay events: {str(e)}") from e

    def create_event(
        self,
        type: EventType,
        channel: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.MEDIUM,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        pattern: CommunicationPattern = CommunicationPattern.PUBLISH_SUBSCRIBE
    ) -> EventSchema:
        """Create a new event.
        
        Args:
            type: Event type
            channel: Target channel
            data: Event data
            priority: Event priority
            correlation_id: Optional correlation ID
            reply_to: Optional reply-to channel
            pattern: Communication pattern
            
        Returns:
            Created event
        """
        return EventSchema(
            id=str(uuid4()),
            type=type,
            channel=channel,
            priority=priority,
            status=EventStatus.PENDING,
            timestamp=datetime.utcnow(),
            data=data,
            correlation_id=correlation_id,
            reply_to=reply_to,
            pattern=pattern,
            service_name=self.service_name
        ) 