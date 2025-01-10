"""Tests for the EventHandler class.

This module contains tests for the EventHandler class, which manages event subscriptions
and dispatches events to registered handlers. Tests cover:
- Event handler registration
- Event dispatching
- Error handling
- Lifecycle management (start/stop)
- Multiple handler support
"""
from typing import Any, Callable, Dict, List, Tuple
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_mock import MockFixture

from src.core.messaging.event_handler import EventHandler
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger

# Test constants
TEST_AGENT_NAME = "TestAgent"
TEST_EVENT_TYPE = "test_event"
TEST_EVENT_DATA = "test_data"

# Test event templates
TEST_EVENT = {
    "type": TEST_EVENT_TYPE,
    "data": TEST_EVENT_DATA
}

@pytest.fixture
def mock_event_system() -> AsyncMock:
    """Create a mock event system for testing.
    
    Returns:
        AsyncMock: Configured event system mock with required async methods.
    """
    mock = AsyncMock(spec=EventSystem)
    mock.is_connected = AsyncMock(return_value=True)
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    return mock

@pytest.fixture
def mock_logger() -> Mock:
    """Create a mock logger for testing.
    
    Returns:
        Mock: Logger mock with standard logging methods.
    """
    return Mock(spec=BaseLogger)

@pytest.fixture
def event_handler(
    mock_event_system: AsyncMock,
    mock_logger: Mock
) -> EventHandler:
    """Create an event handler instance for testing.
    
    Args:
        mock_event_system: Mock event system to use
        mock_logger: Mock logger to use
    
    Returns:
        EventHandler: Configured event handler instance.
    """
    return EventHandler(TEST_AGENT_NAME, mock_event_system, mock_logger)

async def create_test_handler(
    received_events: List[Tuple[str, Dict[str, Any]]],
    handler_name: str
) -> Callable[[Dict[str, Any]], None]:
    """Create a test event handler that records received events.
    
    Args:
        received_events: List to store received events
        handler_name: Name to identify this handler
    
    Returns:
        Callable: Async handler function that records events.
    """
    async def handler(event_data: Dict[str, Any]) -> None:
        received_events.append((handler_name, event_data))
    return handler

class TestEventHandler:
    """Tests for the EventHandler class."""
    
    @pytest.mark.asyncio
    async def test_register_handler(
        self,
        event_handler: EventHandler,
        mock_event_system: AsyncMock
    ) -> None:
        """Test registering an event handler and starting event processing."""
        # Setup
        async def test_handler(event_data: Dict[str, Any]) -> None:
            pass
        
        # Execute
        await event_handler.register_handler(TEST_EVENT_TYPE, test_handler)
        await event_handler.start()
        
        # Verify
        assert TEST_EVENT_TYPE in event_handler._handlers
        mock_event_system.subscribe.assert_awaited_once_with(
            TEST_EVENT_TYPE,
            event_handler._dispatch_event
        )
    
    @pytest.mark.asyncio
    async def test_dispatch_event(self, event_handler: EventHandler) -> None:
        """Test dispatching an event to a registered handler."""
        # Setup
        received_events: List[Tuple[str, Dict[str, Any]]] = []
        test_handler = await create_test_handler(received_events, "test")
        
        await event_handler.register_handler(TEST_EVENT_TYPE, test_handler)
        
        # Execute
        await event_handler._dispatch_event(TEST_EVENT)
        
        # Verify
        assert len(received_events) == 1
        assert received_events[0] == ("test", TEST_EVENT)
    
    @pytest.mark.asyncio
    async def test_dispatch_event_with_error(
        self,
        event_handler: EventHandler,
        mock_logger: Mock
    ) -> None:
        """Test error handling during event dispatch."""
        # Setup
        error_message = "Test error"
        async def error_handler(event_data: Dict[str, Any]) -> None:
            raise ValueError(error_message)
        
        await event_handler.register_handler(TEST_EVENT_TYPE, error_handler)
        
        # Execute
        await event_handler._dispatch_event(TEST_EVENT)
        
        # Verify
        mock_logger.error.assert_called_once_with(
            f"Error handling event {TEST_EVENT_TYPE}: {error_message}"
        )
    
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(
        self,
        event_handler: EventHandler,
        mock_event_system: AsyncMock
    ) -> None:
        """Test the complete lifecycle of starting and stopping event handling."""
        # Setup
        async def test_handler(event_data: Dict[str, Any]) -> None:
            pass
        
        mock_event_system.is_connected = AsyncMock(return_value=False)
        await event_handler.register_handler(TEST_EVENT_TYPE, test_handler)
        
        # Execute start
        await event_handler.start()
        
        # Verify started state
        assert event_handler._listening
        mock_event_system.subscribe.assert_awaited_once_with(
            TEST_EVENT_TYPE,
            event_handler._dispatch_event
        )
        
        # Execute stop
        await event_handler.stop()
        
        # Verify stopped state
        assert not event_handler._listening
        mock_event_system.unsubscribe.assert_awaited_once_with(
            TEST_EVENT_TYPE,
            event_handler._dispatch_event
        )
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_handler: EventHandler) -> None:
        """Test handling multiple event types with different handlers."""
        # Setup
        received_events: List[Tuple[str, Dict[str, Any]]] = []
        handler1 = await create_test_handler(received_events, "handler1")
        handler2 = await create_test_handler(received_events, "handler2")
        
        event1 = {"type": "event1", "data": "test1"}
        event2 = {"type": "event2", "data": "test2"}
        
        await event_handler.register_handler("event1", handler1)
        await event_handler.register_handler("event2", handler2)
        
        # Execute
        await event_handler._dispatch_event(event1)
        await event_handler._dispatch_event(event2)
        
        # Verify
        assert len(received_events) == 2
        assert ("handler1", event1) in received_events
        assert ("handler2", event2) in received_events
    
    @pytest.mark.asyncio
    async def test_unregister_handler(
        self,
        event_handler: EventHandler,
        mock_event_system: AsyncMock
    ) -> None:
        """Test unregistering an event handler."""
        # Setup
        async def test_handler(event_data: Dict[str, Any]) -> None:
            pass
        
        await event_handler.register_handler(TEST_EVENT_TYPE, test_handler)
        await event_handler.start()
        
        # Execute
        await event_handler.unregister_handler(TEST_EVENT_TYPE)
        
        # Verify
        assert TEST_EVENT_TYPE not in event_handler._handlers
        mock_event_system.unsubscribe.assert_awaited_once_with(
            TEST_EVENT_TYPE,
            event_handler._dispatch_event
        ) 