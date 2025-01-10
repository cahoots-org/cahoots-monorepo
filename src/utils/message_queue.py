from typing import Dict, Any, Optional, List, Callable, Awaitable
import json
import asyncio
from datetime import datetime, timedelta
import logging
from redis import Redis
from uuid import uuid4

from .error_handling import SystemError, ErrorCategory, ErrorSeverity, RecoveryStrategy

class MessageState:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

class Message:
    def __init__(
        self,
        payload: Dict[str, Any],
        message_type: str,
        priority: int = 1,
        retry_policy: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid4())
        self.payload = payload
        self.message_type = message_type
        self.priority = priority
        self.retry_policy = retry_policy or {
            "max_retries": 3,
            "base_delay": 1,
            "max_delay": 60
        }
        self.state = MessageState.PENDING
        self.retry_count = 0
        self.created_at = datetime.utcnow()
        self.last_processed_at: Optional[datetime] = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payload": self.payload,
            "message_type": self.message_type,
            "priority": self.priority,
            "retry_policy": self.retry_policy,
            "state": self.state,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        msg = cls(
            payload=data["payload"],
            message_type=data["message_type"],
            priority=data["priority"],
            retry_policy=data["retry_policy"]
        )
        msg.id = data["id"]
        msg.state = data["state"]
        msg.retry_count = data["retry_count"]
        msg.created_at = datetime.fromisoformat(data["created_at"])
        msg.last_processed_at = (
            datetime.fromisoformat(data["last_processed_at"])
            if data["last_processed_at"]
            else None
        )
        return msg

class MessageQueue:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, List[Callable[[Message], Awaitable[None]]]] = {}
        self._processing = False
        
    async def publish(self, message: Message) -> None:
        """Publish a message to the queue with delivery guarantee."""
        try:
            # Store message in Redis
            await self._store_message(message)
            
            # Add to priority queue
            score = message.priority * 1000000000 - message.created_at.timestamp()
            self.redis.zadd(
                f"queue:{message.message_type}",
                {message.id: score}
            )
            
            self.logger.info(f"Published message {message.id} of type {message.message_type}")
            
        except Exception as e:
            raise SystemError(
                message=f"Failed to publish message: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.RETRY,
                original_error=e,
                context={"message_id": message.id}
            )
            
    async def subscribe(
        self,
        message_type: str,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Subscribe to messages of a specific type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        
    async def start_processing(self) -> None:
        """Start processing messages from the queue."""
        self._processing = True
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
            
    async def stop_processing(self) -> None:
        """Stop processing messages."""
        self._processing = False
        
    async def _store_message(self, message: Message) -> None:
        """Store message data in Redis."""
        self.redis.set(
            f"message:{message.id}",
            json.dumps(message.to_dict())
        )
        
    async def _process_messages(self, message_type: str) -> None:
        """Process messages of a specific type."""
        # Get highest priority message
        result = self.redis.zpopmax(f"queue:{message_type}")
        if not result:
            return
            
        message_id = result[0][0]
        message_data = self.redis.get(f"message:{message_id}")
        if not message_data:
            return
            
        message = Message.from_dict(json.loads(message_data))
        message.state = MessageState.PROCESSING
        message.last_processed_at = datetime.utcnow()
        await self._store_message(message)
        
        try:
            # Execute all handlers
            for handler in self._handlers[message_type]:
                await handler(message)
                
            # Mark as completed
            message.state = MessageState.COMPLETED
            await self._store_message(message)
            
        except Exception as e:
            await self._handle_processing_failure(message, e)
            
    async def _handle_processing_failure(
        self,
        message: Message,
        error: Exception
    ) -> None:
        """Handle message processing failure with retry logic."""
        message.retry_count += 1
        
        if message.retry_count >= message.retry_policy["max_retries"]:
            # Move to dead letter queue
            message.state = MessageState.DEAD_LETTER
            await self._store_message(message)
            self.redis.zadd(
                "dead_letter_queue",
                {message.id: datetime.utcnow().timestamp()}
            )
            self.logger.warning(
                f"Message {message.id} moved to dead letter queue after "
                f"{message.retry_count} retries"
            )
        else:
            # Schedule retry
            message.state = MessageState.PENDING
            await self._store_message(message)
            
            delay = min(
                message.retry_policy["base_delay"] * (2 ** (message.retry_count - 1)),
                message.retry_policy["max_delay"]
            )
            
            # Add back to queue with delay
            score = (
                message.priority * 1000000000 -
                (datetime.utcnow() + timedelta(seconds=delay)).timestamp()
            )
            self.redis.zadd(f"queue:{message.message_type}", {message.id: score})
            
    async def _process_dead_letters(self) -> None:
        """Process messages in the dead letter queue."""
        # Implement dead letter queue processing logic here
        # This could include:
        # - Alerting
        # - Manual intervention
        # - Archiving
        pass 