"""Unit tests for queue.py."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, ANY
from uuid import UUID
import json
import asyncio
from cahoots_events.bus.queue import Message, EventQueue
from cahoots_events.bus.types import EventStatus, EventType, PublishError
from cahoots_core.exceptions import QueueError
from cahoots_core.types import RetryPolicy

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def mock_event_system():
    return AsyncMock()

@pytest.fixture
def event_queue(mock_redis, mock_event_system):
    return EventQueue(redis=mock_redis, event_system=mock_event_system)

@pytest.fixture
def sample_message():
    return Message(
        payload={"test": "data"},
        message_type="task.created"  # Using valid event type
    )

@pytest.mark.asyncio
async def test_message_creation():
    """Test message creation with default values."""
    message = Message(
        payload={"test": "data"},
        message_type="task.created"
    )
    assert isinstance(message.id, UUID)
    assert message.payload == {"test": "data"}
    assert message.message_type == "task.created"
    assert message.priority == 1
    assert message.state == EventStatus.PENDING.value
    assert message.retry_count == 0
    assert isinstance(message.created_at, datetime)
    assert message.last_processed_at is None

@pytest.mark.asyncio
async def test_queue_initialization(event_queue):
    """Test queue initialization."""
    assert event_queue._prefix == "queue:"
    assert event_queue._dlq_prefix == "dlq:"
    assert event_queue._handlers == {}
    assert not event_queue._processing

@pytest.mark.asyncio
async def test_queue_publish_message(event_queue, sample_message):
    """Test publishing a message to the queue."""
    # Disable event system for this test
    event_queue.event_system = None
    
    message_id = await event_queue.publish(sample_message)
    assert message_id == str(sample_message.id)
    
    # Verify Redis operations
    event_queue.redis.set.assert_awaited_once()
    event_queue.redis.zadd.assert_awaited_once()

@pytest.mark.asyncio
async def test_queue_publish_dict(event_queue):
    """Test publishing a dictionary as message."""
    # Disable event system for this test
    event_queue.event_system = None
    
    message_dict = {
        "payload": {"test": "data"},
        "message_type": "task.created"
    }
    message_id = await event_queue.publish(message_dict)
    assert UUID(message_id)  # Verify valid UUID
    
    # Verify Redis operations
    event_queue.redis.set.assert_awaited_once()
    event_queue.redis.zadd.assert_awaited_once()

@pytest.mark.asyncio
async def test_queue_publish_redis_error(event_queue, sample_message):
    """Test publishing with Redis error."""
    event_queue.event_system = None  # Disable event system
    event_queue.redis.set.side_effect = Exception("Redis error")

    with pytest.raises(QueueError) as exc_info:
        await event_queue.publish(sample_message)

    assert "Failed to publish message" in str(exc_info.value)
    assert "Redis error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_queue_subscribe_handler(event_queue: EventQueue):
    """Test subscribing message handlers."""
    async def test_handler(message): pass
    
    await event_queue.subscribe("task.created", test_handler)
    assert len(event_queue._handlers.get("task.created")) == 1
    assert event_queue._handlers.get("task.created")[0] == test_handler

@pytest.mark.asyncio
async def test_queue_process_message_success(event_queue, sample_message):
    """Test successful message processing."""
    event_queue.event_system = None  # Disable event system
    handler_called = False
    
    async def test_handler(message):
        nonlocal handler_called
        handler_called = True
        assert message.id == sample_message.id
    
    # Setup Redis responses
    event_queue.redis.zpopmax.return_value = [(str(sample_message.id).encode(), 1.0)]
    event_queue.redis.get.return_value = sample_message.model_dump_json()
    
    # Subscribe handler
    await event_queue.subscribe(sample_message.message_type, test_handler)
    
    # Process messages
    await event_queue._process_messages(sample_message.message_type)
    
    assert handler_called
    assert event_queue.redis.set.await_count >= 2  # Initial store + completion

@pytest.mark.asyncio
async def test_queue_process_message_handler_error(event_queue: EventQueue, sample_message: Message):
    """Test message processing with handler error."""
    event_queue.event_system = None  # Disable event system

    async def failing_handler(message):
        raise Exception("Handler error")
    
    event_queue.register_handler("task.created", failing_handler)
    with pytest.raises(Exception):
        await event_queue.process_message(sample_message)
    
    assert sample_message.state == "failed"

@pytest.mark.asyncio
async def test_queue_start_stop_processing(event_queue):
    """Test starting and stopping queue processing."""
    # Mock the process loop to avoid actual processing
    with patch.object(event_queue, '_process_loop', new_callable=AsyncMock) as mock_loop:
        # Start processing
        await event_queue.start_processing()
        assert event_queue._processing
        assert event_queue._process_task is not None
        mock_loop.assert_called_once()
        
        # Start again should do nothing
        await event_queue.start_processing()
        mock_loop.assert_called_once()  # Still only called once
        
        # Stop processing
        await event_queue.stop_processing()
        assert not event_queue._processing
        assert event_queue._process_task is None

@pytest.mark.asyncio
async def test_queue_process_dead_letters(event_queue, sample_message):
    """Test processing messages from dead letter queue."""
    event_queue.event_system = None  # Disable event system
    
    # Subscribe a handler to ensure message type is registered
    async def test_handler(message): pass
    await event_queue.subscribe(sample_message.message_type, test_handler)
    
    # Setup message in DLQ that's over 7 days old
    old_message = sample_message.model_copy()
    old_message.last_processed_at = datetime.utcnow() - timedelta(days=8)
    
    # Setup Redis responses
    dlq_key = f"dlq:{sample_message.message_type}"
    event_queue.redis.zpopmax = AsyncMock(side_effect=[
        [(str(old_message.id).encode(), 1.0)],  # First call returns old message
        []  # Second call returns empty (no more messages)
    ])
    event_queue.redis.get.return_value = old_message.model_dump_json()
    
    # Process dead letters
    await event_queue._process_dead_letters()
    
    # Verify:
    # 1. Message was retrieved from DLQ
    event_queue.redis.zpopmax.assert_awaited_with(dlq_key)
    assert event_queue.redis.zpopmax.await_count == 2
    
    # 2. Message data was fetched
    event_queue.redis.get.assert_awaited_with(f"message:{old_message.id}")
    
    # 3. Old message was archived
    archive_key = f"archive:{sample_message.message_type}"
    event_queue.redis.zadd.assert_awaited_with(
        archive_key,
        {str(old_message.id): ANY}  # ANY since timestamp will vary
    )

@pytest.mark.asyncio
async def test_queue_processing_flags(event_queue):
    """Test processing flag can be set and cleared."""
    assert not event_queue._processing  # Initial state
    
    event_queue._processing = True
    assert event_queue._processing
    
    event_queue._processing = False
    assert not event_queue._processing 