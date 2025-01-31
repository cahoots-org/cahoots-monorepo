"""Event system client for asynchronous communication using Redis."""
from typing import Dict, Any, Callable, List, Optional, Union
import json
import logging
import asyncio
from collections import defaultdict
from datetime import datetime
import redis.asyncio as redis

from ..exceptions import EventError, EventPublishError, EventSubscriptionError

logger = logging.getLogger(__name__)

class EventClientError(EventError):
    """Base exception for event client errors."""
    pass

class ConnectionError(EventClientError):
    """Exception raised for Redis connection errors."""
    pass

class PublishError(EventPublishError):
    """Exception raised for message publishing errors."""
    pass

class SubscriptionError(EventSubscriptionError):
    """Exception raised for subscription errors."""
    pass

class EventClient:
    """Client for asynchronous communication using Redis pub/sub."""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        dlq_prefix: str = "dlq:",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        heartbeat_interval: float = 5.0
    ):
        """Initialize the event client.
        
        Args:
            redis_client: Redis client instance
            dlq_prefix: Prefix for dead letter queue keys
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            heartbeat_interval: Interval for heartbeat checks
        """
        self.redis = redis_client
        self._pubsub = None
        self._connected = False
        self._handlers = defaultdict(list)
        self._dlq_prefix = dlq_prefix
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task = None
        
    @property
    def is_connected(self) -> bool:
        """Check if event client is connected."""
        return self._connected
        
    async def verify_connection(self) -> bool:
        """Verify connection to Redis is active.
        
        Returns:
            True if connected, False otherwise
            
        Raises:
            ConnectionError: If connection verification fails
        """
        try:
            await self.redis.ping()
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Redis connection failed: {str(e)}")
            
    async def _heartbeat(self) -> None:
        """Send periodic heartbeat to verify connection."""
        while True:
            try:
                await self.verify_connection()
                await asyncio.sleep(self._heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")
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
                self._pubsub = self.redis.pubsub()
                await self._pubsub.subscribe("__heartbeat__")
                
                # Start heartbeat task
                if not self._heartbeat_task:
                    self._heartbeat_task = asyncio.create_task(self._heartbeat())
                    
                self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")
            
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
            await self._pubsub.close()
            self._pubsub = None
            
        self._connected = False
        
    async def publish(
        self,
        channel: str,
        message: Dict[str, Any],
        retry_count: int = 0
    ) -> bool:
        """Publish a message to a channel.
        
        Args:
            channel: Channel to publish to
            message: Message to publish
            retry_count: Current retry attempt
            
        Returns:
            True if published successfully
            
        Raises:
            PublishError: If publishing fails after retries
        """
        try:
            # Add metadata
            message["timestamp"] = datetime.utcnow().isoformat()
            message["retry_count"] = retry_count
            
            # Publish message
            result = await self.redis.publish(channel, json.dumps(message))
            
            if result > 0:
                logger.info(f"Published message to {channel}")
                return True
                
            # No subscribers
            logger.warning(f"No subscribers for channel {channel}")
            return False
            
        except Exception as e:
            if retry_count < self._max_retries:
                logger.warning(
                    f"Failed to publish to {channel}, "
                    f"retrying ({retry_count + 1}/{self._max_retries})"
                )
                await asyncio.sleep(self._retry_delay)
                return await self.publish(channel, message, retry_count + 1)
                
            # Move to DLQ
            dlq_key = f"{self._dlq_prefix}{channel}"
            try:
                await self.redis.lpush(dlq_key, json.dumps(message))
                logger.warning(f"Moved failed message to DLQ: {dlq_key}")
            except Exception as dlq_error:
                logger.error(f"Failed to move message to DLQ: {str(dlq_error)}")
                
            raise PublishError(f"Failed to publish to {channel}: {str(e)}")
            
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Dict[str, Any]], Any],
        pattern: bool = False
    ) -> None:
        """Subscribe to a channel with a message handler.
        
        Args:
            channel: Channel to subscribe to
            handler: Async function to handle messages
            pattern: Whether to use pattern matching
            
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
                
            # Start message processing
            asyncio.create_task(self._process_messages())
            
        except Exception as e:
            raise SubscriptionError(f"Failed to subscribe to {channel}: {str(e)}")
            
    async def _process_messages(self) -> None:
        """Process incoming messages from subscribed channels."""
        try:
            while True:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message["channel"].decode()
                    data = json.loads(message["data"].decode())
                    
                    # Call handlers
                    for handler in self._handlers[channel]:
                        try:
                            await handler(data)
                        except Exception as e:
                            logger.error(
                                f"Handler error for channel {channel}: {str(e)}"
                            )
                            
                await asyncio.sleep(0.01)  # Prevent busy loop
                
        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            # Reconnect on error
            await self.connect()
            await self._process_messages()

# Global client instance
_event_client: Optional[EventClient] = None

def get_event_client(
    redis_client: redis.Redis,
    dlq_prefix: str = "dlq:",
    max_retries: int = 3,
    retry_delay: float = 1.0,
    heartbeat_interval: float = 5.0
) -> EventClient:
    """Get or create the global event client instance.
    
    Args:
        redis_client: Redis client instance
        dlq_prefix: Prefix for dead letter queue keys
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        heartbeat_interval: Interval for heartbeat checks
        
    Returns:
        EventClient instance
    """
    global _event_client
    if _event_client is None:
        _event_client = EventClient(
            redis_client=redis_client,
            dlq_prefix=dlq_prefix,
            max_retries=max_retries,
            retry_delay=retry_delay,
            heartbeat_interval=heartbeat_interval
        )
    return _event_client 