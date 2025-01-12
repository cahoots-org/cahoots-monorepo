"""Tests for the Event System."""
import pytest
from unittest.mock import AsyncMock
import json
from redis.asyncio import Redis

@pytest.mark.asyncio
async def test_publish():
    """Test publish method in isolation."""
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.publish = AsyncMock(return_value=True)
    redis_mock.hset = AsyncMock(return_value=True)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.ping = AsyncMock(return_value=True)
    pubsub_mock = AsyncMock()
    pubsub_mock.ping = AsyncMock(return_value=True)
    redis_mock.pubsub = AsyncMock(return_value=pubsub_mock)
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    
    await system.publish("test_channel", {"test": "data"})
    
    # Verify event was stored and published
    redis_mock.hset.assert_called_once()
    redis_mock.publish.assert_called_once()

@pytest.mark.asyncio
async def test_subscribe():
    """Test subscribe method in isolation."""
    redis_mock = AsyncMock(spec=Redis)
    pubsub_mock = AsyncMock()
    pubsub_mock.ping = AsyncMock(return_value=True)
    pubsub_mock.subscribe = AsyncMock(return_value=True)
    redis_mock.pubsub = AsyncMock(return_value=pubsub_mock)
    redis_mock.ping = AsyncMock(return_value=True)
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    
    async def handler(event): pass
    
    await system.subscribe("test_channel", handler)
    pubsub_mock.subscribe.assert_called_once_with("test_channel")
    assert "test_channel" in system._handlers
    assert handler in system._handlers["test_channel"]

@pytest.mark.asyncio
async def test_unsubscribe():
    """Test unsubscribe method in isolation."""
    redis_mock = AsyncMock(spec=Redis)
    pubsub_mock = AsyncMock()
    pubsub_mock.ping = AsyncMock(return_value=True)
    pubsub_mock.unsubscribe = AsyncMock(return_value=True)
    redis_mock.pubsub = AsyncMock(return_value=pubsub_mock)
    redis_mock.ping = AsyncMock(return_value=True)
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    
    async def handler(event): pass
    system._handlers["test_channel"] = [handler]
    system._pubsub = pubsub_mock
    
    await system.unsubscribe("test_channel", handler)
    pubsub_mock.unsubscribe.assert_called_once_with("test_channel")
    assert "test_channel" not in system._handlers

@pytest.mark.asyncio
async def test_verify_connection():
    """Test verify_connection method in isolation."""
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.ping = AsyncMock(return_value=True)
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    
    result = await system.verify_connection()
    assert result is True
    redis_mock.ping.assert_called_once()
    assert system.is_connected is True

@pytest.mark.asyncio
async def test_verify_connection_failure():
    """Test verify_connection failure case."""
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.ping = AsyncMock(side_effect=Exception("Connection failed"))
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    
    result = await system.verify_connection()
    assert result is False
    redis_mock.ping.assert_called_once()
    assert system.is_connected is False

@pytest.mark.asyncio
async def test_close():
    """Test close method in isolation."""
    redis_mock = AsyncMock(spec=Redis)
    pubsub_mock = AsyncMock()
    pubsub_mock.close = AsyncMock(return_value=True)
    redis_mock.pubsub = AsyncMock(return_value=pubsub_mock)
    
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)
    system._pubsub = pubsub_mock
    system._connected = True
    
    await system.close()
    pubsub_mock.close.assert_called_once()
    assert system._pubsub is None
    assert system.is_connected is False 

@pytest.mark.asyncio
async def test_get_processed_events():
    """Test retrieving processed events."""
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.hgetall = AsyncMock(return_value={
        "events:test:1": json.dumps({
            "type": "test",
            "data": {"test": "data1"},
            "timestamp": "2024-01-01T00:00:00"
        }),
        "events:test:2": json.dumps({
            "type": "test",
            "data": {"test": "data2"},
            "timestamp": "2024-01-01T00:00:01"
        })
    })
    pubsub_mock = AsyncMock()
    pubsub_mock.ping = AsyncMock(return_value=True)
    redis_mock.pubsub = AsyncMock(return_value=pubsub_mock)

    from src.utils.event_system import EventSystem
    system = EventSystem(redis=redis_mock)

    events = await system.get_processed_events("test")
    assert len(events) == 2
    assert events[0]["data"]["test"] == "data1"
    assert events[1]["data"]["test"] == "data2" 