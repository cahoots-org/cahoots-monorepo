"""Tests for the event system."""
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from redis.asyncio import Redis
import json

from src.utils.event_system import EventSystem, DateTimeEncoder

@pytest.fixture
def mock_redis_client() -> Mock:
    """Create a mock Redis client."""
    mock = Mock(spec=Redis)
    # Redis methods are async
    mock.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.close = AsyncMock(return_value=None)
    
    # Set up pubsub
    mock_pubsub = Mock()
    mock_pubsub.subscribe = AsyncMock(return_value=None)
    mock_pubsub.close = AsyncMock(return_value=None)
    mock.pubsub = Mock(return_value=mock_pubsub)
    
    return mock

@pytest.fixture
def event_system(mock_redis_client: Mock) -> EventSystem:
    """Create an event system instance for testing."""
    system = EventSystem()
    system.redis_client = mock_redis_client
    system._connected = True
    system.pubsub = mock_redis_client.pubsub()
    return system

@pytest.mark.asyncio
async def test_event_system_connect(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system connection."""
    event_system._connected = False  # Reset connection state
    await event_system.connect(mock_redis_client)
    assert event_system.is_connected()
    mock_redis_client.ping.assert_awaited_once()

@pytest.mark.asyncio
async def test_event_system_publish(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system publishing."""
    message = {"type": "test", "data": "test_data"}
    await event_system.publish("test_channel", message)

    mock_redis_client.publish.assert_awaited_once_with(
        "test_channel",
        json.dumps(message, cls=DateTimeEncoder)
    )

@pytest.mark.asyncio
async def test_event_system_error_handling(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system error handling."""
    event_system._connected = False  # Reset connection state
    mock_redis_client.ping.side_effect = Exception("Test error")
    with pytest.raises(Exception, match="Test error"):
        await event_system.connect(mock_redis_client)
    assert not event_system.is_connected()

@pytest.mark.asyncio
async def test_event_system_handle_message(event_system: EventSystem) -> None:
    """Test event system message handling."""
    mock_handler = Mock()
    
    # Simulate receiving a message
    message = {"type": "test", "data": "test_data"}
    await event_system.process_message(message, mock_handler)
    
    mock_handler.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_event_system_subscribe(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system subscription."""
    async def handler(message: dict) -> None:
        pass
    
    await event_system.subscribe("test_channel", handler)
    mock_redis_client.pubsub.return_value.subscribe.assert_awaited_once_with("test_channel")
    assert "test_channel" in event_system.handlers

@pytest.mark.asyncio
async def test_event_system_disconnect(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system disconnection."""
    await event_system.disconnect()
    assert not event_system.is_connected()
    mock_redis_client.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_event_system_start_stop_listening(event_system: EventSystem) -> None:
    """Test event system listening."""
    await event_system.start_listening()
    assert event_system._listening
    assert event_system._listen_task is not None
    assert not event_system._listen_task.done()
    
    await event_system.stop_listening()
    assert not event_system._listening
    assert event_system._listen_task is None

@pytest.mark.asyncio
async def test_event_system_verify_connection(event_system: EventSystem, mock_redis_client: Mock) -> None:
    """Test event system connection verification."""
    assert event_system.is_connected()
    
    # Test disconnection detection
    mock_redis_client.ping.side_effect = Exception("Connection lost")
    assert not await event_system.verify_connection() 