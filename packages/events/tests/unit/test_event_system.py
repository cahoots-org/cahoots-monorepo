"""Unit tests for event system functionality."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from core.utils.event_system import EventSystem
from core.models import Event, EventHandler

@pytest.fixture
async def event_system():
    """Create an event system instance."""
    system = EventSystem()
    await system.initialize()
    yield system
    await system.shutdown()

@pytest.fixture
def sample_events():
    """Create sample events for testing."""
    return [
        Event(
            type="task_created",
            data={"id": "task-1", "title": "Test Task"},
            metadata={"priority": "high"}
        ),
        Event(
            type="code_reviewed",
            data={"pr_id": "pr-1", "status": "approved"},
            metadata={"reviewer": "qa-agent"}
        ),
        Event(
            type="test_completed",
            data={"test_id": "test-1", "result": "passed"},
            metadata={"coverage": 85.5}
        )
    ]

@pytest.mark.asyncio
async def test_publish_event(event_system, sample_events):
    """Test event publishing."""
    handler = AsyncMock()
    await event_system.subscribe("task_created", handler)
    
    await event_system.publish(sample_events[0])
    handler.assert_called_once_with(sample_events[0])

@pytest.mark.asyncio
async def test_subscribe_handler(event_system):
    """Test handler subscription."""
    handler = AsyncMock()
    await event_system.subscribe("test_event", handler)
    
    handlers = await event_system.get_handlers("test_event")
    assert handler in handlers

@pytest.mark.asyncio
async def test_unsubscribe_handler(event_system):
    """Test handler unsubscription."""
    handler = AsyncMock()
    await event_system.subscribe("test_event", handler)
    await event_system.unsubscribe("test_event", handler)
    
    handlers = await event_system.get_handlers("test_event")
    assert handler not in handlers

@pytest.mark.asyncio
async def test_multiple_handlers(event_system, sample_events):
    """Test multiple handlers for same event."""
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    
    await event_system.subscribe("task_created", handler1)
    await event_system.subscribe("task_created", handler2)
    
    await event_system.publish(sample_events[0])
    
    handler1.assert_called_once_with(sample_events[0])
    handler2.assert_called_once_with(sample_events[0])

@pytest.mark.asyncio
async def test_pattern_matching(event_system):
    """Test event pattern matching subscription."""
    handler = AsyncMock()
    await event_system.subscribe("test.*", handler)
    
    event1 = Event(type="test.start", data={}, metadata={})
    event2 = Event(type="test.end", data={}, metadata={})
    
    await event_system.publish(event1)
    await event_system.publish(event2)
    
    assert handler.call_count == 2

@pytest.mark.asyncio
async def test_error_handling(event_system, sample_events):
    """Test error handling in event processing."""
    async def error_handler(event):
        raise ValueError("Test error")
    
    await event_system.subscribe("task_created", error_handler)
    
    # Should not raise exception
    await event_system.publish(sample_events[0])

@pytest.mark.asyncio
async def test_event_filtering(event_system):
    """Test event filtering."""
    handler = AsyncMock()
    await event_system.subscribe(
        "test_event",
        handler,
        filter_fn=lambda event: event.metadata.get("priority") == "high"
    )
    
    high_priority = Event(
        type="test_event",
        data={},
        metadata={"priority": "high"}
    )
    low_priority = Event(
        type="test_event",
        data={},
        metadata={"priority": "low"}
    )
    
    await event_system.publish(high_priority)
    await event_system.publish(low_priority)
    
    handler.assert_called_once_with(high_priority)

@pytest.mark.asyncio
async def test_event_transformation(event_system):
    """Test event transformation."""
    handler = AsyncMock()
    
    def transform_fn(event):
        event.data["transformed"] = True
        return event
    
    await event_system.subscribe(
        "test_event",
        handler,
        transform_fn=transform_fn
    )
    
    event = Event(
        type="test_event",
        data={"original": True},
        metadata={}
    )
    
    await event_system.publish(event)
    
    called_event = handler.call_args[0][0]
    assert called_event.data["transformed"]
    assert called_event.data["original"]

@pytest.mark.asyncio
async def test_event_ordering(event_system):
    """Test event processing order."""
    results = []
    
    async def handler1(event):
        results.append(1)
    
    async def handler2(event):
        results.append(2)
    
    await event_system.subscribe("test_event", handler1)
    await event_system.subscribe("test_event", handler2)
    
    event = Event(type="test_event", data={}, metadata={})
    await event_system.publish(event)
    
    assert results == [1, 2]

@pytest.mark.asyncio
async def test_event_replay(event_system, sample_events):
    """Test event replay functionality."""
    handler = AsyncMock()
    await event_system.subscribe("task_created", handler)
    
    # Store events
    for event in sample_events:
        await event_system.publish(event)
    
    # Replay task_created events
    await event_system.replay("task_created")
    
    # Should be called once for original publish and once for replay
    assert handler.call_count == 2 