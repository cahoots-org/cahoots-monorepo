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
from ..utils.metrics import (
    MESSAGE_PUBLISH_COUNTER,
    MESSAGE_PROCESSING_TIME,
    MESSAGE_RETRY_COUNTER,
    MESSAGE_DLQ_COUNTER,
    track_time,
    redis_pool_size,
    redis_pool_maxsize
)
from prometheus_client import Gauge
from ..models.task import Task
from redis.asyncio import Redis
from ..utils.models import BaseMessage

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
    """Event system for handling asynchronous messages."""

    def __init__(self):
        """Initialize event system."""
        self.redis: Optional[Redis] = None
        self._connected = False
        self.dead_letter_queue = "dead_letter_queue"
        self.service_name = "ai_dev_team"
        self.handlers: Dict[str, Callable] = {}
        self.pubsub: Optional[PubSub] = None
        self._running = False
        logger.info("Event system initialized")

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.redis:
            self.redis = Redis(
                host=config.redis.host,
                port=config.redis.port,
                db=config.redis.db,
                client_name=config.redis.client_name
            )
        # Verify connection
        await self.verify_connection()
        self._connected = True
        logger.info("Connected to Redis")

    async def verify_connection(self) -> bool:
        """Verify Redis connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            if not self.redis:
                return False
            await self.redis.ping()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if event system is connected.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected and self.redis is not None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None
        self._connected = False
        logger.info("Disconnected from Redis")

    async def stop_listening(self) -> None:
        """Stop listening for messages."""
        if self.pubsub:
            channels = list(self.handlers.keys())
            for channel in channels:
                self.unsubscribe(channel)
            self.pubsub.close()
            self.pubsub = None
        await self.disconnect()

    def _validate_message(self, message: Dict[str, Any]) -> None:
        """Validate message format and required fields.
        
        Args:
            message: Message to validate
            
        Raises:
            ValidationError: If message is invalid
        """
        if not isinstance(message, dict):
            raise ValidationError("Message must be a dictionary")

        required_fields = {"id", "timestamp", "type", "payload"}
        missing_fields = required_fields - set(message.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        try:
            BaseMessage(**message)
        except Exception as e:
            raise ValidationError(f"Invalid message format: {str(e)}")

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish a message to a channel.
        
        Args:
            channel: Channel to publish to
            message: Message to publish
        """
        try:
            self._validate_message(message)
            
            # Check retry count
            if message.get("retry_count", 0) >= message.get("max_retries", 3):
                logger.warning(
                    f"Message exceeded max retries ({message['retry_count']} >= {message['max_retries']}), "
                    "sending to dead_letter_queue",
                    extra={"service": self.service_name}
                )
                await self.redis.publish(
                    self.dead_letter_queue,
                    json.dumps(message, cls=DateTimeEncoder)
                )
                return

            await self.redis.publish(
                channel,
                json.dumps(message, cls=DateTimeEncoder)
            )

        except ValidationError as e:
            logger.error(
                f"Message validation failed: {str(e)}",
                extra={"service": self.service_name}
            )
            raise

        except Exception as e:
            logger.error(
                f"Failed to publish message: {str(e)}",
                extra={"service": self.service_name}
            )
            raise

    async def subscribe(self, channel: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Subscribe to channel.
        
        Args:
            channel: Channel to subscribe to
            handler: Async function to handle received messages
            
        Raises:
            Exception: If not connected to Redis
        """
        if not self.redis:
            raise Exception("Not connected to Redis")

        if not self.pubsub:
            self.pubsub = self.redis.pubsub()
        
        self.handlers[channel] = handler
        self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to {channel}")

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from channel.
        
        Args:
            channel: Channel to unsubscribe from
        """
        if self.pubsub and channel in self.handlers:
            self.pubsub.unsubscribe(channel)
            del self.handlers[channel]
            logger.info(f"Unsubscribed from {channel}")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle received message.
        
        Args:
            message: Message to handle
        """
        try:
            # Process message
            logger.info(f"Processing message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise 

    async def get_redis(self) -> Optional["Redis"]:
        """Get Redis client.
        
        Returns:
            Redis client if connected, None otherwise
        """
        if not self._connected:
            return None
        return self.redis 

# Global event system instance
_event_system: Optional[EventSystem] = None

def get_event_system() -> EventSystem:
    """Get the global event system instance.
    
    Returns:
        EventSystem: The global event system instance
    """
    global _event_system
    if _event_system is None:
        _event_system = EventSystem()
    return _event_system 