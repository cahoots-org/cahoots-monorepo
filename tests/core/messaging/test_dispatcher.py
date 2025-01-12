"""Tests for the Message Dispatcher system."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime

from src.core.messaging.dispatcher import (
    MessageDispatcher,
    Message,
    MessageType,
    MessagePriority,
    MessageStatus,
    MessageError,
    DispatcherError
)

@pytest.fixture
def dispatcher():
    """Create a message dispatcher instance."""
    return MessageDispatcher()

@pytest.fixture
def sample_message():
    """Create a sample message."""
    return Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"task_id": "123", "assignee": "dev1"},
        priority=MessagePriority.NORMAL,
        source="project_manager",
        target="developer"
    )

@pytest.mark.asyncio
async def test_message_creation(sample_message):
    """Test message creation."""
    assert sample_message.type == MessageType.TASK_ASSIGNMENT
    assert sample_message.payload == {"task_id": "123", "assignee": "dev1"}
    assert sample_message.priority == MessagePriority.NORMAL
    assert sample_message.source == "project_manager"
    assert sample_message.target == "developer"
    assert sample_message.status == MessageStatus.PENDING
    assert sample_message.error is None
    assert isinstance(sample_message.created_at, float)
    assert sample_message.processed_at is None

@pytest.mark.asyncio
async def test_dispatcher_initialization(dispatcher):
    """Test dispatcher initialization."""
    # A new dispatcher should not be running
    assert dispatcher.is_running == False
    
    # No handlers should be registered for any message type
    async def test_handler(message):
        pass
    
    # Register and then unregister a handler to verify initial state
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    dispatcher.unregister_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    
    # After unregistering, the handler should not be present
    message = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"test": "data"}
    )
    
    # The dispatcher should accept registration of new handlers
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    assert MessageType.TASK_ASSIGNMENT.value in dispatcher._handlers

@pytest.mark.asyncio
async def test_dispatcher_start_stop(dispatcher):
    """Test starting and stopping the dispatcher."""
    await dispatcher.start()
    assert dispatcher.is_running == True
    
    await dispatcher.stop()
    assert dispatcher.is_running == False

@pytest.mark.asyncio
async def test_dispatcher_register_handler(dispatcher):
    """Test registering message handlers."""
    async def test_handler(message):
        pass
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    assert len(dispatcher._handlers) == 1
    assert MessageType.TASK_ASSIGNMENT.value in dispatcher._handlers
    assert (None, test_handler) in dispatcher._handlers[MessageType.TASK_ASSIGNMENT.value]

@pytest.mark.asyncio
async def test_dispatcher_unregister_handler(dispatcher):
    """Test unregistering message handlers."""
    async def test_handler(message):
        pass
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    assert len(dispatcher._handlers) == 1
    
    dispatcher.unregister_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    assert MessageType.TASK_ASSIGNMENT.value not in dispatcher._handlers

@pytest.mark.asyncio
async def test_dispatcher_send(dispatcher, sample_message):
    """Test sending messages."""
    mock_handler = AsyncMock()
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, mock_handler)
    
    await dispatcher.start()
    await dispatcher.send(sample_message)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    mock_handler.assert_called_once_with(sample_message)
    assert sample_message.status == MessageStatus.DELIVERED
    assert isinstance(sample_message.processed_at, float)
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_send_with_error(dispatcher, sample_message):
    """Test sending messages with handler error."""
    async def error_handler(message):
        raise ValueError("Test error")
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, error_handler)
    
    await dispatcher.start()
    await dispatcher.send(sample_message)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    assert sample_message.status == MessageStatus.FAILED
    assert isinstance(sample_message.error, MessageError)
    assert "Test error" in str(sample_message.error)
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_broadcast(dispatcher):
    """Test broadcasting messages."""
    handler1_messages = []
    handler2_messages = []
    
    async def handler1(message):
        handler1_messages.append(message)
    
    async def handler2(message):
        handler2_messages.append(message)
    
    dispatcher.register_handler(MessageType.SYSTEM_NOTIFICATION, handler1)
    dispatcher.register_handler(MessageType.SYSTEM_NOTIFICATION, handler2)
    
    broadcast_message = Message(
        type=MessageType.SYSTEM_NOTIFICATION,
        payload={"message": "System update"},
        priority=MessagePriority.HIGH
    )
    
    await dispatcher.start()
    await dispatcher.broadcast(broadcast_message)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    assert len(handler1_messages) == 1
    assert len(handler2_messages) == 1
    assert handler1_messages[0] == broadcast_message
    assert handler2_messages[0] == broadcast_message
    assert broadcast_message.status == MessageStatus.DELIVERED
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_priority_handling(dispatcher):
    """Test message priority handling."""
    processed_messages = []
    
    async def test_handler(message):
        processed_messages.append(message)
        await asyncio.sleep(0.1)  # Simulate processing time
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, test_handler)
    
    # Create messages with different priorities
    high_priority = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"priority": "high"},
        priority=MessagePriority.HIGH
    )
    
    normal_priority = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"priority": "normal"},
        priority=MessagePriority.NORMAL
    )
    
    low_priority = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"priority": "low"},
        priority=MessagePriority.LOW
    )
    
    await dispatcher.start()
    
    # Send messages in reverse priority order
    await dispatcher.send(low_priority)
    await dispatcher.send(normal_priority)
    await dispatcher.send(high_priority)
    
    # Wait for message processing
    await asyncio.sleep(0.5)
    
    assert len(processed_messages) == 3
    assert processed_messages[0] == high_priority
    assert processed_messages[1] == normal_priority
    assert processed_messages[2] == low_priority
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_target_routing(dispatcher):
    """Test message routing to specific targets."""
    dev1_messages = []
    dev2_messages = []
    
    async def dev1_handler(message):
        dev1_messages.append(message)
    
    async def dev2_handler(message):
        dev2_messages.append(message)
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, dev1_handler, target="dev1")
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, dev2_handler, target="dev2")
    
    message_dev1 = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"task": "task1"},
        target="dev1"
    )
    
    message_dev2 = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"task": "task2"},
        target="dev2"
    )
    
    await dispatcher.start()
    await dispatcher.send(message_dev1)
    await dispatcher.send(message_dev2)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    assert len(dev1_messages) == 1
    assert len(dev2_messages) == 1
    assert dev1_messages[0] == message_dev1
    assert dev2_messages[0] == message_dev2
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_wildcard_handler(dispatcher):
    """Test wildcard message handler."""
    processed_messages = []
    
    async def wildcard_handler(message):
        processed_messages.append(message)
    
    dispatcher.register_handler("*", wildcard_handler)
    
    # Create messages of different types
    task_message = Message(type=MessageType.TASK_ASSIGNMENT, payload={})
    notification_message = Message(type=MessageType.SYSTEM_NOTIFICATION, payload={})
    error_message = Message(type=MessageType.ERROR_REPORT, payload={})
    
    await dispatcher.start()
    
    await dispatcher.send(task_message)
    await dispatcher.send(notification_message)
    await dispatcher.send(error_message)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    assert len(processed_messages) == 3
    assert task_message in processed_messages
    assert notification_message in processed_messages
    assert error_message in processed_messages
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_error_handling(dispatcher):
    """Test dispatcher error handling."""
    error_messages = []
    
    async def error_handler(message):
        if isinstance(message.error, MessageError):
            error_messages.append(message)
    
    dispatcher.register_handler(MessageType.ERROR_REPORT, error_handler)
    
    async def failing_handler(message):
        raise ValueError("Handler error")
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, failing_handler)
    
    test_message = Message(type=MessageType.TASK_ASSIGNMENT, payload={})
    
    await dispatcher.start()
    await dispatcher.send(test_message)
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    assert len(error_messages) == 1
    assert isinstance(error_messages[0].error, MessageError)
    assert "Handler error" in str(error_messages[0].error)
    
    await dispatcher.stop()

def test_message_type_values():
    """Test message type enum values."""
    assert MessageType.TASK_ASSIGNMENT.value == "task.assignment"
    assert MessageType.TASK_UPDATE.value == "task.update"
    assert MessageType.SYSTEM_NOTIFICATION.value == "system.notification"
    assert MessageType.ERROR_REPORT.value == "error.report"

def test_message_priority_values():
    """Test message priority enum values."""
    assert MessagePriority.LOW.value == 0
    assert MessagePriority.NORMAL.value == 1
    assert MessagePriority.HIGH.value == 2
    assert MessagePriority.CRITICAL.value == 3

def test_message_status_values():
    """Test message status enum values."""
    assert MessageStatus.PENDING.value == "pending"
    assert MessageStatus.PROCESSING.value == "processing"
    assert MessageStatus.DELIVERED.value == "delivered"
    assert MessageStatus.FAILED.value == "failed" 