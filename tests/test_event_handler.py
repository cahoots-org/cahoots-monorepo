"""Tests for the EventHandler class."""
import pytest
from unittest.mock import AsyncMock, Mock
from src.core.messaging.event_handler import EventHandler
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock(spec=EventSystem)
    mock.is_connected.return_value = True
    return mock

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock(spec=BaseLogger)

@pytest.fixture
def event_handler(mock_event_system, mock_logger):
    """Create an event handler instance."""
    return EventHandler("TestAgent", mock_event_system, mock_logger)

@pytest.mark.asyncio
async def test_register_handler(event_handler, mock_event_system):
    """Test registering an event handler."""
    # Setup
    async def test_handler(event_data):
        pass
    
    # Execute
    await event_handler.register_handler("test_event", test_handler)
    
    # Verify
    assert "test_event" in event_handler._handlers
    mock_event_system.subscribe.assert_awaited_once_with("test_event", event_handler._dispatch_event)

@pytest.mark.asyncio
async def test_dispatch_event(event_handler):
    """Test dispatching an event to registered handler."""
    # Setup
    received_data = None
    async def test_handler(event_data):
        nonlocal received_data
        received_data = event_data
    
    await event_handler.register_handler("test_event", test_handler)
    test_event = {"type": "test_event", "data": "test"}
    
    # Execute
    await event_handler._dispatch_event(test_event)
    
    # Verify
    assert received_data == test_event

@pytest.mark.asyncio
async def test_dispatch_event_with_error(event_handler, mock_logger):
    """Test error handling in event dispatch."""
    # Setup
    async def error_handler(event_data):
        raise ValueError("Test error")
    
    await event_handler.register_handler("test_event", error_handler)
    test_event = {"type": "test_event", "data": "test"}
    
    # Execute
    await event_handler._dispatch_event(test_event)
    
    # Verify
    mock_logger.error.assert_called_once()
    assert "Test error" in mock_logger.error.call_args[0][0]

@pytest.mark.asyncio
async def test_start_stop(event_handler, mock_event_system):
    """Test starting and stopping event handling."""
    # Setup
    async def test_handler(event_data):
        pass

    # Configure mock
    mock_event_system.is_connected.return_value = False
    mock_event_system.connect = AsyncMock()
    mock_event_system.subscribe = AsyncMock()
    mock_event_system.unsubscribe = AsyncMock()

    await event_handler.register_handler("test_event", test_handler)

    # Execute start
    await event_handler.start()

    # Verify start
    assert event_handler._listening is True
    mock_event_system.connect.assert_awaited_once()
    mock_event_system.subscribe.assert_awaited_once_with("test_event", event_handler._dispatch_event)

    # Execute stop
    mock_event_system.is_connected.return_value = True
    await event_handler.stop()

    # Verify stop
    assert event_handler._listening is False
    mock_event_system.unsubscribe.assert_awaited_once_with("test_event", event_handler._dispatch_event)

@pytest.mark.asyncio
async def test_multiple_handlers(event_handler):
    """Test registering and dispatching to multiple handlers."""
    # Setup
    received_events = []
    async def handler1(event_data):
        received_events.append(("handler1", event_data))
    
    async def handler2(event_data):
        received_events.append(("handler2", event_data))
    
    await event_handler.register_handler("event1", handler1)
    await event_handler.register_handler("event2", handler2)
    
    # Execute
    await event_handler._dispatch_event({"type": "event1", "data": "test1"})
    await event_handler._dispatch_event({"type": "event2", "data": "test2"})
    
    # Verify
    assert len(received_events) == 2
    assert received_events[0] == ("handler1", {"type": "event1", "data": "test1"})
    assert received_events[1] == ("handler2", {"type": "event2", "data": "test2"}) 