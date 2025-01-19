"""Event system implementation."""
from typing import Dict, Any, Optional, List, Callable, Awaitable
import logging
import asyncio
from datetime import datetime
import json

from ..models import Event, EventStatus
from ..infrastructure.client import EventClient, EventClientError, SubscriptionError
from ..exceptions import EventSizeLimitExceeded
from cahoots_core.utils.infrastructure.redis.client import get_redis_client

from .types import EventContext, EventError, PublishError
from .queue import EventQueue

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

class EventSystem:
    """Event system for asynchronous communication using Redis."""
    
    def __init__(
        self, 
        redis_client: redis.Redis,
        dlq_prefix: str = "dlq:",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        heartbeat_interval: float = 5.0
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
        self.logger = logging.getLogger(__name__)
        self._dlq_prefix = dlq_prefix
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task = None
        
    @property
    def is_connected(self) -> bool:
        """Check if event system is connected."""
        return self._connected
    
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

    async def subscribe(
        self, 
        channel: str, 
        handler: Callable[[Dict[str, Any]], Any],
        pattern: bool = False
    ) -> None:
        """Subscribe to a channel with a message handler.
        
        Args:
            channel: The channel to subscribe to
            handler: Async function to handle messages
            pattern: Whether to use pattern matching for channel name
            
        Raises:
            SubscriptionError: If subscription fails
            ConnectionError: If not connected
        """
        if not self._connected:
            await self.connect()
            
        try:
            # Add handler
            self._handlers[channel].append(handler)
            
            # Subscribe to channel
            if pattern:
                await self._pubsub.psubscribe(channel)
            else:
                await self._pubsub.subscribe(channel)
        except Exception as e:
            raise SubscriptionError(f"Failed to subscribe to {channel}: {e}") from e
        
    async def unsubscribe(
        self, 
        channel: str, 
        handler: Optional[Callable] = None,
        pattern: bool = False
    ) -> None:
        """Unsubscribe handler(s) from a channel.
        
        Args:
            channel: The channel to unsubscribe from
            handler: Specific handler to remove, or None for all
            pattern: Whether channel uses pattern matching
        """
        if channel in self._handlers:
            if handler:
                self._handlers[channel].remove(handler)
            else:
                self._handlers[channel].clear()
                
            if not self._handlers[channel]:
                if pattern:
                    await self._pubsub.punsubscribe(channel)
                else:
                    await self._pubsub.unsubscribe(channel)
                del self._handlers[channel]

    async def publish(
        self, 
        channel: str, 
        message: Union[Dict[str, Any], EventSchema]
    ) -> str:
        """Publish a message to a channel.
        
        Args:
            channel: The channel to publish to
            message: The message to publish (dict or EventSchema)
            
        Returns:
            str: Event ID of published message
            
        Raises:
            PublishError: If publishing fails
            ConnectionError: If not connected
        """
        if not self._connected:
            await self.connect()
            
        try:
            # Convert EventSchema to dict if needed
            if isinstance(message, EventSchema):
                event_data = message.model_dump()
            else:
                event_data = message
            
            # Add metadata
            event_id = str(uuid.uuid4())
            event_data.update({
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": EventStatus.PENDING.value
            })
            
            # Store message
            event_json = json.dumps(event_data)
            await self.redis.hset(f"events:{channel}", event_id, event_json)
            
            # Publish event ID
            await self._pubsub_client.publish(channel, event_id)
            
            return event_id
        except Exception as e:
            raise PublishError(f"Failed to publish to {channel}: {e}") from e

    async def _store_dlq_message(
        self, 
        channel: str, 
        message: Dict[str, Any], 
        error: Exception
    ) -> None:
        """Store failed message in dead letter queue.
        
        Args:
            channel: Original channel
            message: Failed message
            error: Error that caused failure
        """
        dlq_key = f"{self._dlq_prefix}{channel}"
        dlq_message = {
            "original_message": message,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        await self.redis.lpush(dlq_key, json.dumps(dlq_message))
        self.logger.error(f"Message moved to DLQ {dlq_key}: {error}")
        
    async def get_dlq_messages(self, channel: str) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue.
        
        Args:
            channel: Channel to get DLQ messages for
            
        Returns:
            List of DLQ messages with metadata
        """
        dlq_key = f"{self._dlq_prefix}{channel}"
        messages = []
        
        # Get all messages from list
        raw_messages = await self.redis.lrange(dlq_key, 0, -1)
        for raw_msg in raw_messages:
            try:
                message = json.loads(raw_msg)
                messages.append(message)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode DLQ message: {raw_msg}")
                continue
                
        return messages
        
    async def retry_dlq_messages(self, channel: str) -> None:
        """Retry processing messages from dead letter queue.
        
        Args:
            channel: Channel to retry messages for
        """
        dlq_messages = await self.get_dlq_messages(channel)
        
        for message in dlq_messages:
            if message["retry_count"] < self._max_retries:
                # Increment retry count
                message["retry_count"] += 1
                
                # Republish original message
                await self.publish(channel, message["original_message"])
                
                # Remove from DLQ
                dlq_key = f"{self._dlq_prefix}{channel}"
                await self.redis.lrem(dlq_key, 1, json.dumps(message))
                
                # Add delay between retries
                await asyncio.sleep(self._retry_delay)
                
    async def process_messages(self, timeout: float = 0.1) -> None:
        """Process incoming messages from subscribed channels.
        
        Args:
            timeout: Time to wait for messages in seconds
            
        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            await self.connect()
            
        try:
            async with asyncio.timeout(timeout):
                start_time = asyncio.get_event_loop().time()
                while True:
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        break
                        
                    # Get next message
                    message = await self._pubsub.get_message(ignore_subscribe_messages=True)
                    if not message:
                        await asyncio.sleep(0.01)
                        continue
                        
                    if message['type'] == 'message':
                        channel = message['channel'].decode('utf-8')
                        event_id = message['data'].decode('utf-8')
                        
                        if channel in self._handlers:
                            try:
                                # Get event data
                                event_json = await self.redis.hget(f"events:{channel}", event_id)
                                if not event_json:
                                    self.logger.error(f"Event {event_id} not found in channel {channel}")
                                    continue
                                    
                                event_data = json.loads(event_json)
                                
                                # Update status
                                event_data["status"] = EventStatus.PROCESSING.value
                                await self.redis.hset(
                                    f"events:{channel}",
                                    event_id,
                                    json.dumps(event_data)
                                )
                                
                                # Process with all handlers
                                for handler in self._handlers[channel]:
                                    try:
                                        await handler(event_data)
                                    except Exception as e:
                                        self.logger.error(f"Handler failed for event {event_id}: {e}")
                                        event_data["status"] = EventStatus.FAILED.value
                                        await self._store_dlq_message(channel, event_data, e)
                                        continue
                                
                                # Update status and store processed event
                                event_data["status"] = EventStatus.COMPLETED.value
                                await self.redis.hset(
                                    f"processed_events:{channel}",
                                    event_id,
                                    json.dumps(event_data)
                                )
                                
                                # Delete from active events
                                await self.redis.hdel(f"events:{channel}", event_id)
                                        
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Failed to decode event {event_id}: {e}")
                            except Exception as e:
                                self.logger.error(f"Error processing event {event_id}: {e}")
                                
        except asyncio.TimeoutError:
            pass  # Expected on timeout
        except Exception as e:
            self.logger.error(f"Error in message processing loop: {e}")
            raise  # Re-raise unexpected errors
            
    async def get_events(
        self, 
        channel: str,
        status: Optional[EventStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get events from a channel with optional filtering.
        
        Args:
            channel: Channel to get events from
            status: Optional status to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of events matching criteria
        """
        events = []
        
        # Get events based on status
        if status == EventStatus.COMPLETED:
            key = f"processed_events:{channel}"
        else:
            key = f"events:{channel}"
            
        event_data = await self.redis.hgetall(key)
        
        for event_id, event_json in event_data.items():
            try:
                event = json.loads(event_json)
                
                # Apply filters
                if status and event.get("status") != status.value:
                    continue
                    
                if start_time:
                    event_time = datetime.fromisoformat(event["timestamp"])
                    if event_time < start_time:
                        continue
                        
                if end_time:
                    event_time = datetime.fromisoformat(event["timestamp"])
                    if event_time > end_time:
                        continue
                
                events.append(event)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode event {event_id}")
                continue
                
        return events
        
    async def close(self) -> None:
        """Close event system and cleanup resources."""
        await self.disconnect() 