"""Tests for the event system."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.utils.event_system import EventSystem, BaseMessage, ValidationError
from datetime import datetime
from typing import Dict, AsyncGenerator
import json
import asyncio

pytestmark = pytest.mark.asyncio

@pytest.fixture
def event_system_mock() -> EventSystem:
    """Return a mock event system with properly mocked Redis client."""
    event_system = EventSystem()
    
    # Create Redis mock with all required async methods
    redis_mock = AsyncMock()
    redis_mock.publish = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    
    # Create PubSub mock
    pubsub_mock = AsyncMock()
    pubsub_mock.subscribe = MagicMock()  # Synchronous operation
    pubsub_mock.unsubscribe = MagicMock()  # Synchronous operation
    pubsub_mock.close = AsyncMock()  # This one is async
    
    # Setup Redis mock to return PubSub mock synchronously
    redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
    
    # Attach to event system
    event_system.redis = redis_mock
    event_system._connected = True
    
    return event_system

async def test_event_system_connect(redis_mock: AsyncMock):
    """Test event system connection."""
    event_system = EventSystem()
    event_system.redis = redis_mock
    
    await event_system.connect()
    redis_mock.ping.assert_called_once()

async def test_event_system_disconnect(redis_mock: AsyncMock):
    """Test event system disconnection."""
    event_system = EventSystem()
    event_system.redis = redis_mock
    
    await event_system.disconnect()
    redis_mock.close.assert_called_once()

async def test_publish_message(event_system_mock: EventSystem, sample_message: Dict):
    """Test publishing a message."""
    channel = "test_channel"
    await event_system_mock.publish(channel, sample_message)
    
    event_system_mock.redis.publish.assert_called_once()
    call_args = event_system_mock.redis.publish.call_args[0]
    assert call_args[0] == channel
    assert isinstance(call_args[1], str)  # Verify JSON serialization

async def test_publish_invalid_message(event_system_mock: EventSystem):
    """Test publishing an invalid message."""
    invalid_message = {"invalid": "message"}  # Missing required fields
    
    with pytest.raises(ValidationError):
        await event_system_mock.publish("test_channel", invalid_message)

async def test_subscribe_handler(event_system_mock: EventSystem):
    """Test subscribing to a channel."""
    received_messages = []
    
    async def test_handler(message):
        received_messages.append(message)
    
    channel = "test_channel"
    
    # Test subscription
    await event_system_mock.subscribe(channel, test_handler)
    assert channel in event_system_mock.handlers
    assert event_system_mock.handlers[channel] == test_handler
    
    # Test unsubscription
    await event_system_mock.unsubscribe(channel)
    assert channel not in event_system_mock.handlers
    
    # Test cleanup
    await event_system_mock.stop_listening()
    assert not event_system_mock.handlers

async def test_message_validation(event_system_mock: EventSystem):
    """Test message validation."""
    # Test valid message
    valid_message = BaseMessage(
        id="test-1",
        timestamp=datetime.utcnow(),
        type="test",
        payload={"key": "value"},
        retry_count=0,
        max_retries=3
    )
    await event_system_mock.publish("test_channel", valid_message.dict())
    event_system_mock.redis.publish.assert_called_once()

    # Test invalid message format (not a dict)
    with pytest.raises(ValidationError):
        await event_system_mock.publish("test_channel", "not a dict")

    # Test missing required fields
    invalid_message = {"type": "test"}
    with pytest.raises(ValidationError):
        await event_system_mock.publish("test_channel", invalid_message)

    # Test invalid field types
    invalid_types_message = {
        "id": 123,  # should be string
        "timestamp": "not a datetime",
        "type": "test",
        "payload": "not a dict",
        "retry_count": "not an int",
        "max_retries": "not an int"
    }
    with pytest.raises(ValidationError):
        await event_system_mock.publish("test_channel", invalid_types_message)

@pytest.mark.parametrize("retry_count,should_retry", [
    (0, True),
    (1, True),
    (2, True),
    (3, False),
    (4, False),
])
async def test_message_retry_logic(
    event_system_mock: EventSystem,
    retry_count: int,
    should_retry: bool
):
    """Test message retry logic."""
    message = BaseMessage(
        id="test-1",
        timestamp=datetime.utcnow(),
        type="test",
        payload={"key": "value"},
        retry_count=retry_count,
        max_retries=3
    ).dict()

    await event_system_mock.publish("test_channel", message)
    event_system_mock.redis.publish.assert_called_once()
    
    call_args = event_system_mock.redis.publish.call_args[0]
    published_msg = json.loads(call_args[1])

    if should_retry:
        # Message should be published to original channel
        assert call_args[0] == "test_channel"
    else:
        # Message should be published to dead letter queue
        assert call_args[0] == event_system_mock.dead_letter_queue
        
    # Verify message contents
    assert published_msg["id"] == message["id"]
    assert published_msg["type"] == message["type"]
    assert published_msg["payload"] == message["payload"]
    assert published_msg["retry_count"] == message["retry_count"]
    assert published_msg["max_retries"] == message["max_retries"] 