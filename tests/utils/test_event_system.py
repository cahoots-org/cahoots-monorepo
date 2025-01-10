"""Tests for the Event System."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import List, Union
from datetime import datetime
import json
from uuid import uuid4

from src.utils.event_system import EventSystem
from src.utils.event_constants import (
    EventSchema,
    EventType,
    EventPriority,
    EventStatus,
    EventError,
    CommunicationPattern
)

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (EventType, EventPriority, EventStatus, CommunicationPattern)):
            return obj.value
        return super().default(obj)

class PubSubMock:
    """Mock Redis pubsub object."""
    def __init__(self):
        self.channels = set()
        self.messages = []

    def subscribe(self, channel):
        """Subscribe to a channel."""
        self.channels.add(channel)

    def unsubscribe(self, channel):
        """Unsubscribe from a channel."""
        self.channels.discard(channel)

    def get_message(self, ignore_subscribe_messages=True):
        """Get next message."""
        return self.messages.pop(0) if self.messages else None

@pytest.fixture
def redis_mock():
    """Create a Redis mock."""
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.publish = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.keys = AsyncMock(return_value=[])
    
    pubsub = PubSubMock()
    mock.pubsub = Mock(return_value=pubsub)
    
    return mock

@pytest.fixture
async def event_system(redis_mock):
    """Create an event system instance."""
    system = EventSystem(redis=redis_mock, service_name="test_service")
    await system.connect()
    yield system
    await system.disconnect()

@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return {
        "id": str(uuid4()),
        "type": EventType.TASK_CREATED,
        "channel": "task",
        "data": {"task_id": "123", "title": "Test Task"},
        "timestamp": datetime.utcnow()
    }

@pytest.mark.asyncio
async def test_event_creation(sample_event):
    """Test event creation."""
    event = EventSchema(**sample_event)
    assert event.type == EventType.TASK_CREATED
    assert event.data == {"task_id": "123", "title": "Test Task"}
    assert event.status == EventStatus.PENDING

@pytest.mark.asyncio
async def test_event_system_initialization(event_system):
    """Test event system initialization."""
    assert event_system.is_connected is True
    assert event_system.service_name == "test_service"
    assert len(event_system._handlers) == 0

@pytest.mark.asyncio
async def test_event_system_publish(event_system, sample_event):
    """Test event publishing."""
    event = EventSchema(**sample_event)
    await event_system.publish(event)
    event_system.redis.publish.assert_called_once()
    event_system.redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_event_system_publish_with_error(event_system, sample_event):
    """Test event publishing with handler error."""
    event = EventSchema(**sample_event)
    event_system.redis.publish.side_effect = Exception("Redis error")
    
    with pytest.raises(EventError, match="Failed to publish event"):
        await event_system.publish(event)
    
    assert event.status == EventStatus.FAILED

@pytest.mark.asyncio
async def test_event_replay(event_system, sample_event):
    """Test event replay functionality."""
    event = EventSchema(**sample_event)
    event_system.redis.keys.return_value = [f"event:{event.id}"]
    event_system.redis.get.return_value = event.model_dump_json()
    
    replayed = await event_system.replay_events("task")
    assert len(replayed) == 1
    assert replayed[0].type == EventType.TASK_CREATED

@pytest.mark.asyncio
async def test_service_name(event_system):
    """Test service name."""
    assert event_system.service_name == "test_service"

@pytest.mark.asyncio
async def test_subscribe_unsubscribe(event_system):
    """Test subscribe and unsubscribe functionality."""
    async def handler(event):
        pass
    
    channel = "test_channel"
    await event_system.subscribe(channel, handler)
    assert channel in event_system._handlers
    assert handler in event_system._handlers[channel]
    
    await event_system.unsubscribe(channel, handler)
    assert channel not in event_system._handlers

def test_event_type_values():
    """Test event type enumeration values."""
    assert EventType.TASK_CREATED.value == "task_created"
    assert EventType.STORY_ASSIGNED.value == "story_assigned"
    assert EventType.DESIGN_CREATED.value == "design_created"

def test_event_priority_values():
    """Test event priority enumeration values."""
    assert EventPriority.LOW.value == "low"
    assert EventPriority.MEDIUM.value == "medium"
    assert EventPriority.HIGH.value == "high"
    assert EventPriority.CRITICAL.value == "critical"

def test_event_status_values():
    """Test event status enumeration values."""
    assert EventStatus.PENDING.value == "pending"
    assert EventStatus.PROCESSING.value == "processing"
    assert EventStatus.COMPLETED.value == "completed"
    assert EventStatus.FAILED.value == "failed"

def test_communication_patterns():
    """Test communication pattern values."""
    assert CommunicationPattern.PUBLISH_SUBSCRIBE.value == "pub_sub"
    assert CommunicationPattern.REQUEST_RESPONSE.value == "req_resp"
    assert CommunicationPattern.BROADCAST.value == "broadcast" 