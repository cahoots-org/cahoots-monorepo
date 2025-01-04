"""Event system for handling asynchronous messages."""
import json
import os
import asyncio
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool, SSLConnection
from redis.asyncio.retry import Retry
from redis.asyncio.client import PubSub
from redis.backoff import ExponentialBackoff
from typing import Callable, Dict, Any, Optional, Union, List, Set, AsyncGenerator, Awaitable
from pydantic import BaseModel, ValidationError as PydanticValidationError
from datetime import datetime
from ..utils.logger import Logger
from ..utils.config import config
from ..utils.task_manager import TaskManager
from ..utils.metrics import (
    MESSAGE_PUBLISH_COUNTER,
    MESSAGE_PROCESSING_TIME,
    MESSAGE_RETRY_COUNTER,
    MESSAGE_DLQ_COUNTER,
    MESSAGE_ERROR_COUNTER,
    track_time,
    redis_pool_size,
    redis_pool_maxsize
)
from prometheus_client import Gauge
from ..models.task import Task
from redis.asyncio import Redis
from ..utils.models import BaseMessage
import time

class ValidationError(Exception):
    """Custom validation error for event system."""
    pass

# Define available channels
CHANNELS = {
    "system": "system",
    "project_manager": "project_manager",
    "developer": "developer",
    "ux_designer": "ux_designer",
    "tester": "tester",
    "story_assigned": "story_assigned",
    "pr_created": "pr_created",
    "pr_merged": "pr_merged",
    "task_completed": "task_completed"
}

# Define retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1,  # seconds
    "max_delay": 60,  # seconds
    "exponential_base": 2
}

# Define standard event types
class EventTypes:
    TASK_STARTED = "task_started"
    TASK_BLOCKED = "task_blocked"
    TASK_RESUMED = "task_resumed"
    TASK_FAILED = "task_failed"
    PR_CREATED = "pr_created"
    PR_REVIEWED = "pr_reviewed"
    TESTS_STARTED = "tests_started"
    TESTS_FAILED = "tests_failed"
    TESTS_PASSED = "tests_passed"
    STORY_ASSIGNED = "story_assigned"

logger = Logger("EventSystem")

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    
    def default(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class EventSystem:
    """Event system for pub/sub messaging."""

    def __init__(self) -> None:
        """Initialize event system."""
        self.logger = Logger("EventSystem")
        self.redis_client: Optional[Redis] = None
        self.pubsub: Optional[PubSub] = None
        self._connected = False
        self._listening = False
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self._task_manager = TaskManager("EventSystem")
        self._listen_task: Optional[asyncio.Task] = None
        self.logger.info("Event system initialized")

    async def connect(self, redis_client: Optional[Redis] = None) -> None:
        """Connect to Redis.
        
        Args:
            redis_client: Optional Redis client to use. If not provided, a new one will be created.
        """
        if self._connected:
            return

        try:
            if redis_client:
                self.redis_client = redis_client
            else:
                # Create Redis client with retry logic
                retry = Retry(ExponentialBackoff(cap=10, base=1), 3)
                
                # Construct Redis URL from config
                redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
                if config.redis.password and config.redis.password.get_secret_value():
                    redis_url = f"redis://:{config.redis.password.get_secret_value()}@{config.redis.host}:{config.redis.port}/{config.redis.db}"
                
                self.redis_client = await Redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    retry=retry,
                    retry_on_timeout=True
                )
            
            # Verify connection
            await self.redis_client.ping()
            
            # Create pubsub instance
            self.pubsub = self.redis_client.pubsub()
            self._connected = True
            self.logger.info("Connected to Redis")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
            raise

    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self.redis_client is not None

    async def disconnect(self) -> None:
        """Disconnect from Redis and clean up resources."""
        await self.stop_listening()
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        self._connected = False
        self.logger.info("Event system disconnected")

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish a message to a channel."""
        if not self._connected or not self.redis_client:
            raise RuntimeError("Event system not connected")
        
        try:
            await self.redis_client.publish(channel, json.dumps(message, cls=DateTimeEncoder))
            MESSAGE_PUBLISH_COUNTER.labels(channel=channel).inc()
        except Exception as e:
            self.logger.error(f"Failed to publish message to {channel}: {e}")
            MESSAGE_ERROR_COUNTER.labels(channel=channel).inc()
            raise

    async def subscribe(self, channel: str, handler: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None) -> None:
        """Subscribe to a channel and optionally register a message handler."""
        if not self._connected or not self.pubsub:
            raise RuntimeError("Event system not connected")
        
        try:
            await self.pubsub.subscribe(channel)
            if handler:
                self.handlers[channel] = handler
            self.logger.info(f"Subscribed to channel: {channel}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {channel}: {e}")
            raise

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        if not self._connected or not self.pubsub:
            raise RuntimeError("Event system not connected")
        
        try:
            await self.pubsub.unsubscribe(channel)
            if channel in self.handlers:
                del self.handlers[channel]
            self.logger.info(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from {channel}: {e}")
            raise

    async def start_listening(self) -> None:
        """Start listening for messages."""
        if not self._connected or not self.pubsub:
            raise RuntimeError("Event system not connected")
        
        if self._listening:
            return
        
        self.logger.info("Started listening for messages")
        self._listening = True
        
        # Create a background task for listening
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        """Background loop for listening to messages."""
        try:
            while self._listening and self._connected:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                    if message and isinstance(message, dict):
                        channel = message.get("channel", "unknown")
                        MESSAGE_PUBLISH_COUNTER.labels(channel=channel).inc()
                        if channel and channel in self.handlers:
                            data = message.get("data")
                            if isinstance(data, str):
                                try:
                                    parsed_data = json.loads(data)
                                    await self.process_message(parsed_data, self.handlers[channel])
                                except json.JSONDecodeError:
                                    self.logger.error("Failed to decode message data")
                                    MESSAGE_ERROR_COUNTER.labels(channel=channel).inc()
                    await asyncio.sleep(0.01)  # Prevent busy loop
                except Exception as e:
                    self.logger.error(f"Error in message listener: {e}")
                    MESSAGE_RETRY_COUNTER.labels(channel="unknown").inc()
                    await asyncio.sleep(1)  # Basic retry delay
        except asyncio.CancelledError:
            self.logger.info("Message listener cancelled")
            self._listening = False
        except Exception as e:
            self.logger.error(f"Fatal error in message listener: {e}")
            self._listening = False
            raise

    async def stop_listening(self) -> None:
        """Stop listening for messages."""
        self._listening = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        if self.pubsub:
            try:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            except Exception as e:
                self.logger.error(f"Error stopping listener: {e}")
        self.logger.info("Stopped listening for messages")

    async def get_message(self) -> Optional[Dict[str, Any]]:
        """Get a message from Redis pubsub.
        
        Returns:
            Optional[Dict[str, Any]]: Message data if available, None otherwise
        """
        if not self._connected or not self.pubsub:
            return None
        
        try:
            message = await self.pubsub.get_message(ignore_subscribe_messages=True)
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, str):
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        self.logger.error("Failed to decode message data")
                        MESSAGE_ERROR_COUNTER.labels(channel="unknown").inc()
                        return None
        except Exception as e:
            self.logger.error(f"Error getting message: {e}")
            MESSAGE_ERROR_COUNTER.labels(channel="unknown").inc()
        return None

    async def process_message(
        self,
        message: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Process a message with its handler.
        
        Args:
            message: Message to process
            handler: Handler function to call
        """
        try:
            with track_time(MESSAGE_PROCESSING_TIME.labels(channel=message.get("channel", "unknown"))):
                await handler(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            MESSAGE_ERROR_COUNTER.labels(channel=message.get("channel", "unknown")).inc()

    async def verify_connection(self) -> bool:
        """Verify Redis connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            return False 