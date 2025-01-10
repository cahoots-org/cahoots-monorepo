"""Tests for the Message Dispatcher component."""
import pytest
import asyncio
from datetime import datetime
from src.core.messaging.dispatcher import (
    Message,
    MessageDispatcher,
    MessageType,
    MessagePriority,
    MessageStatus,
    MessageError,
    DispatcherError
)

@pytest.fixture
def dispatcher():
    """Create a message dispatcher instance for testing."""
    return MessageDispatcher()

@pytest.fixture
def test_message():
    """Create a test message."""
    return Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"task_id": "123", "assignee": "test_user"},
        priority=MessagePriority.NORMAL,
        source="test_source",
        target="test_target"
    )

@pytest.mark.asyncio
async def test_dispatcher_initialization(dispatcher):
    """Test message dispatcher initialization."""
    assert not dispatcher.is_running
    assert dispatcher._handlers == {}
    assert len(dispatcher._queues) == len(MessagePriority)

@pytest.mark.asyncio
async def test_dispatcher_start_stop(dispatcher):
    """Test starting and stopping the dispatcher."""
    await dispatcher.start()
    assert dispatcher.is_running
    assert len(dispatcher._tasks) == len(MessagePriority)
    
    await dispatcher.stop()
    assert not dispatcher.is_running
    assert not dispatcher._tasks

@pytest.mark.asyncio
async def test_handler_registration(dispatcher):
    """Test message handler registration and unregistration."""
    async def handler(message):
        pass
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, handler)
    assert len(dispatcher._handlers[MessageType.TASK_ASSIGNMENT.value]) == 1
    
    dispatcher.unregister_handler(MessageType.TASK_ASSIGNMENT, handler)
    assert len(dispatcher._handlers[MessageType.TASK_ASSIGNMENT.value]) == 0

@pytest.mark.asyncio
async def test_message_sending(dispatcher, test_message):
    """Test message sending and processing."""
    received_messages = []
    
    async def handler(message):
        received_messages.append(message)
    
    dispatcher.register_handler(test_message.type, handler)
    await dispatcher.start()
    
    await dispatcher.send(test_message)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert len(received_messages) == 1
    assert received_messages[0].type == test_message.type
    assert received_messages[0].payload == test_message.payload
    assert received_messages[0].status == MessageStatus.DELIVERED
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_message_broadcasting(dispatcher, test_message):
    """Test message broadcasting."""
    received_messages = []
    
    async def handler(message):
        received_messages.append(message)
    
    dispatcher.register_handler(test_message.type, handler)
    await dispatcher.start()
    
    await dispatcher.broadcast(test_message)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert len(received_messages) == 1
    assert received_messages[0].target is None  # Target should be cleared for broadcast
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_message_priority_ordering(dispatcher):
    """Test that messages are processed in priority order."""
    received_messages = []
    
    async def handler(message):
        received_messages.append(message)
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, handler)
    await dispatcher.start()
    
    # Create messages with different priorities
    messages = [
        Message(
            type=MessageType.TASK_ASSIGNMENT,
            payload={"priority": priority.name},
            priority=priority
        )
        for priority in [
            MessagePriority.LOW,
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL
        ]
    ]
    
    # Send messages in random order
    for message in messages:
        await dispatcher.send(message)
    
    await asyncio.sleep(0.1)  # Allow time for processing
    
    # Verify messages were processed in priority order
    priorities = [message.priority for message in received_messages]
    assert priorities == sorted(
        priorities,
        key=lambda p: (p.value, messages[priorities.index(p)].created_at)
    )
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_message_error_handling(dispatcher):
    """Test error handling during message processing."""
    async def failing_handler(message):
        raise ValueError("Test error")
    
    dispatcher.register_handler(MessageType.TASK_ASSIGNMENT, failing_handler)
    await dispatcher.start()
    
    test_message = Message(
        type=MessageType.TASK_ASSIGNMENT,
        payload={"task_id": "123"}
    )
    
    await dispatcher.send(test_message)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert test_message.status == MessageStatus.FAILED
    assert isinstance(test_message.error, MessageError)
    assert "Test error" in str(test_message.error)
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_target_specific_handlers(dispatcher, test_message):
    """Test target-specific message handlers."""
    target_handler_called = False
    general_handler_called = False
    
    async def target_handler(message):
        nonlocal target_handler_called
        target_handler_called = True
    
    async def general_handler(message):
        nonlocal general_handler_called
        general_handler_called = True
    
    dispatcher.register_handler(
        test_message.type,
        target_handler,
        target=test_message.target
    )
    dispatcher.register_handler(test_message.type, general_handler)
    await dispatcher.start()
    
    await dispatcher.send(test_message)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert target_handler_called
    assert general_handler_called
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_wildcard_handlers(dispatcher, test_message):
    """Test wildcard message handlers."""
    received_messages = []
    
    async def wildcard_handler(message):
        received_messages.append(message)
    
    dispatcher.register_handler("*", wildcard_handler)
    await dispatcher.start()
    
    await dispatcher.send(test_message)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert len(received_messages) == 1
    assert received_messages[0] == test_message
    
    await dispatcher.stop()

@pytest.mark.asyncio
async def test_dispatcher_not_running_error(dispatcher, test_message):
    """Test error when sending message to stopped dispatcher."""
    with pytest.raises(DispatcherError):
        await dispatcher.send(test_message)

@pytest.mark.asyncio
async def test_message_processing_time(dispatcher, test_message):
    """Test message processing time tracking."""
    async def slow_handler(message):
        await asyncio.sleep(0.1)
    
    dispatcher.register_handler(test_message.type, slow_handler)
    await dispatcher.start()
    
    await dispatcher.send(test_message)
    await asyncio.sleep(0.2)  # Allow time for processing
    
    assert test_message.processed_at is not None
    assert test_message.processed_at > test_message.created_at
    
    await dispatcher.stop() 