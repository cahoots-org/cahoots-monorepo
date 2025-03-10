"""Message queue implementation using Redis."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json import timedelta_isoformat
from redis.asyncio import Redis

from cahoots_core.exceptions import QueueError

from ..exceptions import EventError
from .types import EventPriority, EventSchema, EventStatus, EventType, PublishError

if TYPE_CHECKING:
    from .system import EventSystem

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Message in the queue system."""

    id: UUID = Field(default_factory=uuid4)
    payload: Dict[str, Any]
    message_type: str
    priority: int = 1
    retry_policy: Dict[str, Any] = Field(
        default={"max_retries": 3, "base_delay": 1, "max_delay": 60}
    )
    state: str = EventStatus.PENDING.value
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_processed_at: Optional[datetime] = None

    @property
    def model_serializer(self):
        """Custom serialization."""
        return {
            "id": str,
            "created_at": lambda dt: dt.isoformat() if dt else None,
            "last_processed_at": lambda dt: dt.isoformat() if dt else None,
        }

    def to_event(self) -> EventSchema:
        """Convert message to event schema."""
        return EventSchema(
            id=str(self.id),
            type=self.message_type,
            payload=self.payload,
            status=self.state,
            created_at=self.created_at,
            last_processed_at=self.last_processed_at,
        )


class EventQueue:
    """Message queue implementation using Redis."""

    def __init__(
        self,
        redis: Redis,
        event_system: Optional["EventSystem"] = None,
        prefix: str = "queue:",
        dlq_prefix: str = "dlq:",
    ):
        """Initialize message queue.

        Args:
            redis: Redis client instance
            event_system: Optional event system for notifications
            prefix: Prefix for queue keys
            dlq_prefix: Prefix for dead letter queue keys
        """
        self.redis = redis
        self.event_system = event_system
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, List[Callable[[Message], Awaitable[None]]]] = {}
        self._processing = False
        self._prefix = prefix
        self._dlq_prefix = dlq_prefix
        self._process_task: Optional[asyncio.Task] = None

    def _get_queue_key(self, message_type: str) -> str:
        """Get Redis key for queue."""
        return f"{self._prefix}{message_type}"

    def _get_dlq_key(self, message_type: str) -> str:
        """Get Redis key for dead letter queue."""
        return f"{self._dlq_prefix}{message_type}"

    async def publish(self, message: Union[Message, Dict[str, Any]]) -> str:
        """Publish message to queue."""
        if isinstance(message, dict):
            message = Message(**message)

        try:
            # Store message data
            message_json = message.model_dump_json()
            await self.redis.set(f"message:{message.id}", message_json)

            # Add to queue with priority-based score
            score = message.priority * 1000000000 - datetime.utcnow().timestamp()
            await self.redis.zadd(
                self._get_queue_key(message.message_type), {str(message.id): score}
            )

            # Notify via event system
            if self.event_system:
                try:
                    event = message.to_event()
                    await self.event_system.publish(
                        f"queue.{message.message_type}.published", event
                    )
                except PublishError as e:
                    self.logger.warning(f"Failed to publish event: {e}")

            return str(message.id)

        except Exception as e:
            raise QueueError(
                message=f"Failed to publish message {message.id}: {str(e)}",
                details={
                    "message_type": message.message_type,
                    "message_id": str(message.id),
                    "error": str(e),
                    "operation": "publish",
                },
            )

    async def subscribe(
        self, message_type: str, handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Subscribe to messages of a specific type.

        Args:
            message_type: Type of messages to handle
            handler: Async function to handle messages
        """
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._processing:
            try:
                # Process messages for each type
                for message_type in self._handlers:
                    await self._process_messages(message_type)

                # Process dead letter queue
                await self._process_dead_letters()

            except Exception as e:
                self.logger.error(f"Error in message processing loop: {str(e)}")

            await asyncio.sleep(0.1)  # Prevent CPU spinning

    async def start_processing(self) -> None:
        """Start processing messages from the queue."""
        if self._processing:
            return

        self._processing = True
        self._process_task = asyncio.create_task(self._process_loop())

    async def stop_processing(self) -> None:
        """Stop processing messages."""
        if not self._processing:
            return

        self._processing = False
        if self._process_task:
            await self._process_task
            self._process_task = None

    async def _process_messages(self, message_type: str) -> None:
        """Process messages of a specific type."""
        # Get highest priority message
        result = await self.redis.zpopmax(self._get_queue_key(message_type))
        if not result:
            return

        message_id = result[0][0].decode("utf-8")
        message_data = await self.redis.get(f"message:{message_id}")
        if not message_data:
            return

        try:
            message = Message.model_validate_json(message_data)
            message.state = EventStatus.PROCESSING.value
            message.last_processed_at = datetime.utcnow()
            await self._store_message(message)

            # Execute all handlers
            for handler in self._handlers[message_type]:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error(f"Handler failed for message {message.id}: {e}")
                    await self._handle_processing_failure(message, e)
                    return

            # Mark as completed
            message.state = EventStatus.COMPLETED.value
            await self._store_message(message)

            # Notify via event system
            if self.event_system:
                try:
                    event = message.to_event()
                    await self.event_system.publish(f"queue.{message_type}.completed", event)
                except PublishError as e:
                    self.logger.warning(f"Failed to publish completion event: {e}")

        except Exception as e:
            raise QueueError(
                message=f"Failed to process message {message_id}: {str(e)}",
                details={
                    "message_type": message_type,
                    "message_id": message_id,
                    "error": str(e),
                    "operation": "process",
                },
            )

    async def _store_message(self, message: Message) -> None:
        """Store message data in Redis."""
        await self.redis.set(f"message:{message.id}", message.model_dump_json())

    async def _handle_processing_failure(self, message: Message, error: Exception) -> None:
        """Handle message processing failure with retry logic."""
        message.retry_count += 1

        if message.retry_count >= message.retry_policy["max_retries"]:
            # Move to dead letter queue
            message.state = EventStatus.FAILED.value
            await self._store_message(message)

            dlq_key = self._get_dlq_key(message.message_type)
            await self.redis.zadd(dlq_key, {str(message.id): datetime.utcnow().timestamp()})

            # Notify via event system
            if self.event_system:
                try:
                    event = message.to_event()
                    await self.event_system.publish(f"queue.{message.message_type}.failed", event)
                except PublishError as e:
                    self.logger.warning(f"Failed to publish failure event: {e}")

            self.logger.warning(
                f"Message {message.id} moved to DLQ after " f"{message.retry_count} retries"
            )
        else:
            # Schedule retry
            message.state = EventStatus.PENDING.value
            await self._store_message(message)

            delay = min(
                message.retry_policy["base_delay"] * (2 ** (message.retry_count - 1)),
                message.retry_policy["max_delay"],
            )

            # Add back to queue with delay
            score = (
                message.priority * 1000000000
                - (datetime.utcnow() + timedelta(seconds=delay)).timestamp()
            )
            await self.redis.zadd(
                self._get_queue_key(message.message_type), {str(message.id): score}
            )

            # Notify via event system
            if self.event_system:
                try:
                    event = message.to_event()
                    await self.event_system.publish(f"queue.{message.message_type}.retrying", event)
                except PublishError as e:
                    self.logger.warning(f"Failed to publish retry event: {e}")

    async def _process_dead_letters(self) -> None:
        """Process messages in the dead letter queue."""
        # Get all message types
        message_types = set(self._handlers.keys())

        for message_type in message_types:
            dlq_key = self._get_dlq_key(message_type)

            while True:
                # Get oldest failed message
                result = await self.redis.zpopmax(dlq_key)
                if not result:
                    break

                message_id_bytes, timestamp = result[0]
                message_id = message_id_bytes.decode("utf-8")
                message_data = await self.redis.get(f"message:{message_id}")

                if message_data:
                    try:
                        message = Message.model_validate_json(message_data)

                        # Archive message after certain time
                        age = datetime.utcnow() - message.last_processed_at
                        if age > timedelta(days=7):  # Archive after 7 days
                            # Move to archive
                            await self.redis.zadd(
                                f"archive:{message_type}", {message_id: timestamp}
                            )

                            self.logger.info(
                                f"Archived failed message {message_id} " f"after {age.days} days"
                            )
                    except Exception as e:
                        self.logger.error(f"Failed to process DLQ message {message_id}: {e}")

    async def get_queue_length(self, message_type: str) -> int:
        """Get number of messages in queue.

        Args:
            message_type: Type of messages to count

        Returns:
            int: Number of messages in queue
        """
        return await self.redis.zcard(self._get_queue_key(message_type))

    async def get_dlq_length(self, message_type: str) -> int:
        """Get number of messages in dead letter queue.

        Args:
            message_type: Type of messages to count

        Returns:
            int: Number of messages in DLQ
        """
        return await self.redis.zcard(self._get_dlq_key(message_type))

    async def clear_queue(self, message_type: str) -> None:
        """Clear all messages from queue.

        Args:
            message_type: Type of messages to clear
        """
        await self.redis.delete(self._get_queue_key(message_type))

    async def clear_dlq(self, message_type: str) -> None:
        """Clear all messages from dead letter queue.

        Args:
            message_type: Type of messages to clear
        """
        await self.redis.delete(self._get_dlq_key(message_type))

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a message type.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def process_message(self, message: Message) -> None:
        """Process a single message.

        Args:
            message: Message to process
        """
        if message.message_type not in self._handlers:
            return

        try:
            for handler in self._handlers[message.message_type]:
                await handler(message)
            message.state = "completed"
        except Exception as e:
            message.state = "failed"
            message.retry_count += 1
            raise e
