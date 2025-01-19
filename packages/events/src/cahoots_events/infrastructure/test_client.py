"""Unit tests for event client module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from .client import (
    EventClient,
    EventClientError,
    ConnectionError,
    PublishError,
    SubscriptionError,
    get_event_client
)

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = AsyncMock()
    mock_client.pubsub.return_value = AsyncMock()
    return mock_client

@pytest.fixture
def event_client(mock_redis):
    """Create an EventClient instance with mocked Redis."""
    return EventClient(redis_client=mock_redis)

@pytest.mark.asyncio
async def test_verify_connection_success(event_client, mock_redis):
    """Test successful connection verification."""
    mock_redis.ping.return_value = True
    
    result = await event_client.verify_connection()
    
    assert result is True
    assert event_client.is_connected is True
    mock_redis.ping.assert_called_once()

@pytest.mark.asyncio
async def test_verify_connection_failure(event_client, mock_redis):
    """Test failed connection verification."""
    mock_redis.ping.side_effect = Exception("Connection failed")
    
    with pytest.raises(ConnectionError, match="Redis connection failed"):
        await event_client.verify_connection()
    
    assert event_client.is_connected is False
    mock_redis.ping.assert_called_once()

@pytest.mark.asyncio
async def test_connect_success(event_client, mock_redis):
    """Test successful connection."""
    mock_redis.ping.return_value = True
    mock_pubsub = mock_redis.pubsub.return_value
    
    await event_client.connect()
    
    assert event_client.is_connected is True
    mock_redis.ping.assert_called_once()
    mock_redis.pubsub.assert_called_once()
    mock_pubsub.subscribe.assert_called_once_with("__heartbeat__")

@pytest.mark.asyncio
async def test_connect_failure(event_client, mock_redis):
    """Test failed connection."""
    mock_redis.ping.side_effect = Exception("Connection failed")
    
    with pytest.raises(ConnectionError, match="Failed to connect"):
        await event_client.connect()
    
    assert event_client.is_connected is False
    mock_redis.ping.assert_called_once()

@pytest.mark.asyncio
async def test_disconnect(event_client):
    """Test disconnection."""
    # Setup
    event_client._pubsub = AsyncMock()
    event_client._heartbeat_task = AsyncMock()
    event_client._connected = True
    
    await event_client.disconnect()
    
    assert event_client.is_connected is False
    event_client._pubsub.unsubscribe.assert_called_once()
    event_client._pubsub.close.assert_called_once()
    assert event_client._pubsub is None
    assert event_client._heartbeat_task is None

@pytest.mark.asyncio
async def test_publish_success(event_client, mock_redis):
    """Test successful message publishing."""
    channel = "test_channel"
    message = {"key": "value"}
    mock_redis.publish.return_value = 1
    
    result = await event_client.publish(channel, message)
    
    assert result is True
    mock_redis.publish.assert_called_once()
    call_args = mock_redis.publish.call_args
    assert call_args[0][0] == channel
    published_message = json.loads(call_args[0][1])
    assert published_message["key"] == "value"
    assert "timestamp" in published_message
    assert published_message["retry_count"] == 0

@pytest.mark.asyncio
async def test_publish_no_subscribers(event_client, mock_redis):
    """Test publishing with no subscribers."""
    mock_redis.publish.return_value = 0
    
    result = await event_client.publish("test_channel", {"key": "value"})
    
    assert result is False
    mock_redis.publish.assert_called_once()

@pytest.mark.asyncio
async def test_publish_retry_success(event_client, mock_redis):
    """Test successful message publishing after retry."""
    mock_redis.publish.side_effect = [Exception("First attempt"), 1]
    
    result = await event_client.publish("test_channel", {"key": "value"})
    
    assert result is True
    assert mock_redis.publish.call_count == 2

@pytest.mark.asyncio
async def test_publish_move_to_dlq(event_client, mock_redis):
    """Test moving failed message to DLQ."""
    mock_redis.publish.side_effect = Exception("Failed")
    
    with pytest.raises(PublishError, match="Failed to publish"):
        await event_client.publish("test_channel", {"key": "value"})
    
    assert mock_redis.publish.call_count == event_client._max_retries + 1
    mock_redis.lpush.assert_called_once()
    dlq_key = f"{event_client._dlq_prefix}test_channel"
    assert mock_redis.lpush.call_args[0][0] == dlq_key

@pytest.mark.asyncio
async def test_subscribe_success(event_client, mock_redis):
    """Test successful channel subscription."""
    mock_redis.ping.return_value = True
    mock_pubsub = mock_redis.pubsub.return_value
    
    async def handler(message):
        pass
    
    await event_client.subscribe("test_channel", handler)
    
    assert len(event_client._handlers["test_channel"]) == 1
    mock_pubsub.subscribe.assert_called_with("test_channel")

@pytest.mark.asyncio
async def test_subscribe_pattern_success(event_client, mock_redis):
    """Test successful pattern subscription."""
    mock_redis.ping.return_value = True
    mock_pubsub = mock_redis.pubsub.return_value
    
    async def handler(message):
        pass
    
    await event_client.subscribe("test*", handler, pattern=True)
    
    assert len(event_client._handlers["test*"]) == 1
    mock_pubsub.psubscribe.assert_called_with("test*")

@pytest.mark.asyncio
async def test_subscribe_failure(event_client, mock_redis):
    """Test failed subscription."""
    mock_redis.ping.return_value = True
    mock_pubsub = mock_redis.pubsub.return_value
    mock_pubsub.subscribe.side_effect = Exception("Subscribe failed")
    
    async def handler(message):
        pass
    
    with pytest.raises(SubscriptionError, match="Failed to subscribe"):
        await event_client.subscribe("test_channel", handler)

@pytest.mark.asyncio
async def test_process_messages(event_client, mock_redis):
    """Test message processing."""
    # Setup
    mock_pubsub = mock_redis.pubsub.return_value
    mock_handler = AsyncMock()
    event_client._handlers["test_channel"].append(mock_handler)
    event_client._pubsub = mock_pubsub
    
    # Mock message
    message = {
        "channel": b"test_channel",
        "data": json.dumps({"key": "value"}).encode()
    }
    
    # Setup pubsub to return one message then None
    mock_pubsub.get_message.side_effect = [message, None]
    
    # Run message processing (will stop after processing one message)
    await event_client._process_messages()
    
    # Verify handler was called with decoded message
    mock_handler.assert_called_once_with({"key": "value"})

@pytest.mark.asyncio
async def test_process_messages_handler_error(event_client, mock_redis):
    """Test message processing with handler error."""
    # Setup
    mock_pubsub = mock_redis.pubsub.return_value
    mock_handler = AsyncMock(side_effect=Exception("Handler error"))
    event_client._handlers["test_channel"].append(mock_handler)
    event_client._pubsub = mock_pubsub
    
    # Mock message
    message = {
        "channel": b"test_channel",
        "data": json.dumps({"key": "value"}).encode()
    }
    
    # Setup pubsub to return one message then None
    mock_pubsub.get_message.side_effect = [message, None]
    
    # Run message processing (should handle error gracefully)
    await event_client._process_messages()
    
    # Verify handler was called
    mock_handler.assert_called_once_with({"key": "value"})

def test_get_event_client():
    """Test global client instance creation."""
    mock_redis = AsyncMock()
    
    client1 = get_event_client(mock_redis)
    client2 = get_event_client(mock_redis)
    
    # Should return same instance
    assert client1 == client2 