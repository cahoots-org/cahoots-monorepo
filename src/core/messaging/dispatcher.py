"""Message dispatcher implementation."""
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union, Set
import asyncio
from datetime import datetime
import logging
from dataclasses import dataclass, field
from contextlib import suppress

class MessageType(Enum):
    """Message types."""
    TASK_ASSIGNMENT = "task.assignment"
    TASK_UPDATE = "task.update"
    SYSTEM_NOTIFICATION = "system.notification"
    ERROR_REPORT = "error.report"

class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class MessageStatus(Enum):
    """Message status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"  # New status for cancelled messages

class MessageError(Exception):
    """Message processing error."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class DispatcherError(Exception):
    """Dispatcher-specific errors."""
    pass

@dataclass
class Message:
    """Message class for inter-component communication."""
    type: Union[MessageType, str]
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    source: Optional[str] = None
    target: Optional[str] = None
    status: MessageStatus = field(default=MessageStatus.PENDING)
    error: Optional[MessageError] = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    processed_at: Optional[float] = None

class MessageDispatcher:
    """Message dispatcher for inter-component communication."""

    def __init__(self):
        """Initialize the message dispatcher."""
        self._handlers: Dict[str, List[tuple[Optional[str], Callable]]] = {}
        self._queues = {
            priority: asyncio.Queue() for priority in MessagePriority
        }
        self._tasks: Set[asyncio.Task] = set()
        self._running = False
        self._cleanup_event = asyncio.Event()
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the message dispatcher."""
        if self._running:
            return

        self._running = True
        self._cleanup_event.clear()
        
        # Create a task for each priority queue
        for priority in MessagePriority:
            task = asyncio.create_task(self._process_queues())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def stop(self):
        """Stop the message dispatcher and clean up resources."""
        if not self._running:
            return

        self._running = False
        self._cleanup_event.set()

        # Cancel all pending messages
        for queue in self._queues.values():
            while not queue.empty():
                try:
                    message = queue.get_nowait()
                    message.status = MessageStatus.CANCELLED
                except asyncio.QueueEmpty:
                    break

        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to complete
        with suppress(asyncio.CancelledError):
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        
        # Clear all queues
        self._queues.clear()

    def register_handler(self, message_type: Union[MessageType, str], handler: Callable, target: Optional[str] = None):
        """Register a message handler."""
        if isinstance(message_type, MessageType):
            message_type = message_type.value

        if message_type not in self._handlers:
            self._handlers[message_type] = []
        
        handler_tuple = (target, handler)
        if handler_tuple not in self._handlers[message_type]:
            self._handlers[message_type].append(handler_tuple)

    def unregister_handler(self, message_type: Union[MessageType, str], handler: Callable, target: Optional[str] = None):
        """Unregister a message handler."""
        if isinstance(message_type, MessageType):
            message_type = message_type.value

        if message_type in self._handlers:
            handler_tuple = (target, handler)
            try:
                self._handlers[message_type].remove(handler_tuple)
                if not self._handlers[message_type]:
                    del self._handlers[message_type]
            except ValueError:
                pass  # Handler not found, ignore

    async def send(self, message: Message) -> None:
        """Send a message to registered handlers."""
        if not self._running:
            raise DispatcherError("Dispatcher is not running")

        try:
            if isinstance(message.type, MessageType):
                message_type = message.type.value
            else:
                message_type = message.type
                
            await self._queues[message.priority].put(message)
            self.logger.debug(f"Sent message {message_type} with priority {message.priority.name}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            message.status = MessageStatus.FAILED
            message.error = MessageError("Failed to send message", e)
            raise

    async def broadcast(self, message: Message) -> None:
        """Broadcast a message to all handlers of its type."""
        # For broadcasts, clear the target to ensure delivery to all handlers
        message.target = None
        await self.send(message)

    async def _process_queues(self) -> None:
        """Process all queues in priority order."""
        priorities = sorted(MessagePriority, key=lambda p: -p.value)  # Higher priorities first
        
        while self._running:
            try:
                messages_processed = False
                # Check each priority queue in order
                for priority in priorities:
                    queue = self._queues[priority]
                    
                    # Process all messages in this priority queue
                    while not queue.empty():
                        try:
                            message = queue.get_nowait()
                            try:
                                await self._process_message(message)
                                messages_processed = True
                            except Exception as e:
                                self.logger.error(f"Error processing message: {e}")
                                message.status = MessageStatus.FAILED
                                message.error = MessageError(str(e), e)
                            finally:
                                queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                
                # If no messages were processed, wait a bit before checking again
                if not messages_processed:
                    await asyncio.sleep(0.01)
                
                # Check if we should stop
                if self._cleanup_event.is_set():
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in queue processing: {e}")
                if self._cleanup_event.is_set():
                    break

    async def _process_message(self, message: Message) -> None:
        """Process a single message."""
        if message.status == MessageStatus.CANCELLED:
            return

        message.status = MessageStatus.PROCESSING
        message_type = message.type.value if isinstance(message.type, MessageType) else message.type
        
        # Get handlers for this message type
        handlers = []
        if message_type in self._handlers:
            for target, handler in self._handlers[message_type]:
                if message.target is None or target is None or message.target == target:
                    handlers.append(handler)
        
        # Get wildcard handlers
        if "*" in self._handlers:
            for target, handler in self._handlers["*"]:
                if message.target is None or target is None or message.target == target:
                    handlers.append(handler)
        
        if not handlers:
            self.logger.warning(f"No handlers found for message type: {message_type}")
            message.status = MessageStatus.DELIVERED
            message.processed_at = datetime.now().timestamp()
            return
            
        try:
            # Execute handlers concurrently
            tasks = [
                asyncio.create_task(handler(message))
                for handler in handlers
            ]
            
            if tasks:
                # Wait for all handlers with timeout
                done, pending = await asyncio.wait(tasks, timeout=5.0)
                
                # Cancel any remaining tasks
                for task in pending:
                    task.cancel()
                
                # Wait for cancelled tasks to complete
                with suppress(asyncio.CancelledError):
                    await asyncio.gather(*pending, return_exceptions=True)
                
                # Check for errors
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        raise MessageError(f"Handler error: {str(e)}", e)
                        
                message.status = MessageStatus.DELIVERED
                message.processed_at = datetime.now().timestamp()
                
        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error = MessageError(str(e), e)
            raise

    @property
    def is_running(self) -> bool:
        """Get the running state of the dispatcher."""
        return self._running 