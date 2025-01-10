"""Tests for the BaseAgent class.

This module contains tests for the BaseAgent class, which is the base class for all agents
in the system. It tests initialization, event handling, health status updates, and other
core functionality.
"""
from typing import Dict, Any, AsyncGenerator, cast
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
import asyncio
import time
import json

from src.agents.base_agent import BaseAgent
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger
from src.utils.model import Model
from src.utils.task_manager import TaskManager
from src.core.messaging.event_handler import EventHandler

# Test constants
TEST_MODEL_NAME = "test_model"
TEST_STORY_ID = "test123"
TEST_STORY_TITLE = "Test Story"
HEALTH_CHECK_INTERVAL = 0.1  # Small interval for testing

class TestAgent(BaseAgent):
    """Concrete test implementation of BaseAgent for testing purposes.
    
    This class implements the abstract methods from BaseAgent to allow testing
    of the base functionality.
    """
    __test__ = False  # Prevent pytest from collecting this class
        
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages for testing.
        
        Args:
            message: The system message to handle
        """
        self.logger.info(f"Test agent received system message: {message}")
        
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment for testing.
        
        Args:
            message: The story assignment message
            
        Returns:
            Dict containing the response status and data
        """
        return {
            "status": "success",
            "data": {"message": "Story handled by test agent"}
        }

@pytest.fixture
def mock_event_system() -> Mock:
    """Create a mock event system with all required methods.
    
    Returns:
        AsyncMock: Configured mock event system
    """
    mock = Mock(spec=EventSystem)
    mock.is_connected = False
    mock.connect = AsyncMock()
    mock.redis = Mock()
    mock.redis.set = AsyncMock()
    mock.redis.delete = Mock()
    return mock

@pytest.fixture
def mock_logger() -> Mock:
    """Create a mock logger.
    
    Returns:
        Mock: Configured mock logger
    """
    return Mock(spec=BaseLogger)

@pytest.fixture
def mock_model() -> AsyncMock:
    """Create a mock model with response generation.
    
    Returns:
        AsyncMock: Configured mock model
    """
    mock = AsyncMock(spec=Model)
    mock.generate_response = AsyncMock(return_value="Test response")
    return mock

@pytest.fixture
def mock_task_manager() -> Mock:
    """Create a mock task manager with required methods.
    
    Returns:
        Mock: Configured mock task manager
    """
    mock = Mock(spec=TaskManager)
    mock.create_task = Mock()
    mock.cancel_all = AsyncMock()
    return mock

@pytest.fixture
def mock_event_handler() -> Mock:
    """Create a mock EventHandler instance."""
    mock = Mock(spec=EventHandler)
    mock.register_handler = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create a mock BaseLogger instance."""
    return Mock(spec=BaseLogger)

@pytest.fixture
async def base_agent(
    mock_event_system: Mock,
    mock_logger: Mock,
    mock_model: AsyncMock,
    mock_task_manager: Mock,
    mock_event_handler: Mock,
    mock_base_logger: Mock
) -> AsyncGenerator[TestAgent, None]:
    """Create a base agent instance with mocked dependencies.
    
    Args:
        mock_event_system: Mock event system
        mock_logger: Mock logger
        mock_model: Mock model
        mock_task_manager: Mock task manager
        mock_event_handler: Mock event handler
        mock_base_logger: Mock base logger
        
    Yields:
        TestAgent: Configured test agent instance
    """
    with patch("src.agents.base_agent.Model", return_value=mock_model), \
         patch("src.agents.base_agent.TaskManager", return_value=mock_task_manager):
        agent = TestAgent(TEST_MODEL_NAME, event_system=mock_event_system, start_listening=False)
        agent.logger = mock_logger
        agent._task_manager = mock_task_manager
        agent.event_handler = mock_event_handler
        agent.logger = mock_base_logger
        # Mock the event handler methods
        agent.event_handler.start = AsyncMock()
        agent.event_handler.stop = AsyncMock()
        agent.event_handler.register_handler = AsyncMock()
        yield agent
        await agent.stop()

@pytest.mark.asyncio
async def test_init_success(mock_event_system: Mock, mock_logger: Mock, mock_model: AsyncMock, mock_task_manager: Mock, mock_event_handler: Mock, mock_base_logger: Mock) -> None:
    """Test successful agent initialization with all dependencies.
    
    Should verify:
    - Correct model name assignment
    - Event system setup
    - Logger configuration
    - Task manager initialization
    - Health check task creation
    """
    with patch("src.agents.base_agent.Model") as mock_model_class, \
         patch("src.agents.base_agent.TaskManager") as mock_task_manager_class:
        mock_model = AsyncMock()
        mock_model_class.return_value = mock_model
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        
        agent = TestAgent(TEST_MODEL_NAME, event_system=mock_event_system, start_listening=False)
        agent.logger = mock_logger
        agent._task_manager = mock_task_manager
        agent.event_handler = mock_event_handler
        
        assert agent.model_name == TEST_MODEL_NAME
        assert agent.event_system == mock_event_system
        assert agent.logger == mock_logger
        assert isinstance(agent._task_manager, Mock)
        mock_task_manager.create_task.assert_called_once()  # Health check task
        
@pytest.mark.asyncio
async def test_init_failure(mock_event_system: Mock, mock_logger: Mock) -> None:
    """Test agent initialization failure handling.
    
    Should verify proper exception propagation when Model initialization fails.
    """
    with patch("src.agents.base_agent.Model", side_effect=Exception("Test error")):
        with pytest.raises(Exception, match="Test error"):
            TestAgent(TEST_MODEL_NAME, event_system=mock_event_system)

@pytest.mark.asyncio
async def test_setup_events(base_agent: TestAgent) -> None:
    """Test event handler setup and registration.
    
    Should verify:
    - System message handler registration
    - Story assignment handler registration
    """
    await base_agent.setup_events()
    
    base_agent.event_handler.register_handler.assert_has_awaits([
        call("system", base_agent.handle_system_message),
        call("story_assigned", base_agent.handle_story_assigned)
    ])

@pytest.mark.asyncio
async def test_setup_events_already_connected(base_agent: TestAgent) -> None:
    """Test setup_events when event system is already connected."""
    base_agent.event_system.is_connected = True
    await base_agent.setup_events()
    
    # Verify connect was not called
    base_agent.event_system.connect.assert_not_called()
    
    # Verify handlers were registered
    base_agent.event_handler.register_handler.assert_has_awaits([
        call("system", base_agent.handle_system_message),
        call("story_assigned", base_agent.handle_story_assigned)
    ])

@pytest.mark.asyncio
async def test_start_stop(base_agent: TestAgent) -> None:
    """Test agent lifecycle management.
    
    Should verify:
    - Event handler start on agent start
    - Event handler stop on agent stop
    - Task cancellation on stop
    - Health status cleanup on stop
    """
    # Start agent
    await base_agent.start()
    base_agent.event_handler.start.assert_awaited_once()
    
    # Stop agent
    await base_agent.stop()
    base_agent.event_handler.stop.assert_awaited_once()
    base_agent._task_manager.cancel_all.assert_awaited_once()
    base_agent.event_system.redis.delete.assert_called_once_with(
        f"health:{base_agent.__class__.__name__}"
    )

@pytest.mark.asyncio
async def test_managed_operation(base_agent: TestAgent) -> None:
    """Test the managed operation context manager.
    
    Should verify:
    - Agent start on context enter
    - Agent stop on context exit
    - Task cleanup on context exit
    """
    async with base_agent.managed_operation() as agent:
        assert agent == base_agent
        base_agent.event_handler.start.assert_awaited_once()
    
    base_agent.event_handler.stop.assert_awaited_once()
    base_agent._task_manager.cancel_all.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_system_message(base_agent: TestAgent) -> None:
    """Test system message handling.
    
    Should verify proper logging of received system messages.
    """
    message = {"type": "system", "command": "test"}
    await base_agent.handle_system_message(message)
    base_agent.logger.info.assert_called_once_with(
        "Test agent received system message: {'type': 'system', 'command': 'test'}"
    )

@pytest.mark.asyncio
async def test_handle_story_assigned(base_agent: TestAgent) -> None:
    """Test story assignment handling.
    
    Should verify:
    - Correct response format
    - Success status
    - Expected message content
    """
    message = {
        "type": "story_assigned",
        "story_id": TEST_STORY_ID,
        "title": TEST_STORY_TITLE
    }
    response = await base_agent.handle_story_assigned(message)
    assert response == {
        "status": "success",
        "data": {"message": "Story handled by test agent"}
    }

@pytest.mark.asyncio
async def test_health_status_update(base_agent: TestAgent) -> None:
    """Test health status update mechanism.
    
    Should verify:
    - Health status data format
    - Status value
    - Agent type
    - Timestamp accuracy
    """
    # Mock asyncio.sleep to avoid waiting
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        # Set up mock redis set
        base_agent.event_system.redis.set = AsyncMock()
        
        # Run one iteration
        mock_sleep.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await base_agent._update_health_status()
            
        # Get the actual timestamp from the call
        call_args = base_agent.event_system.redis.set.call_args
        assert call_args is not None
        key, value_str = call_args[0]
        assert key == f"health:{base_agent.__class__.__name__}"
        
        # Parse and verify the health data
        health_data = json.loads(value_str)
        assert health_data["status"] == "healthy"
        assert health_data["agent_type"] == base_agent.__class__.__name__
        assert isinstance(health_data["timestamp"], (int, float))
        assert abs(health_data["timestamp"] - time.time()) < 2  # Within 2 seconds
        
        # Verify sleep was called
        mock_sleep.assert_called_once_with(5)

@pytest.mark.asyncio
async def test_health_status_update_failure(base_agent: TestAgent) -> None:
    """Test health status update failure handling.
    
    Should verify proper error logging when Redis update fails.
    """
    # Mock asyncio.sleep to avoid waiting
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        # Set up mock redis set to fail
        base_agent.event_system.redis.set = AsyncMock(side_effect=Exception("Redis error"))
        
        # Run one iteration
        mock_sleep.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await base_agent._update_health_status()
            
        # Verify error was logged
        base_agent.logger.error.assert_called_with(
            "Failed to update health status: Redis error"
        )
        
        # Verify shorter sleep was used
        mock_sleep.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_init_with_start_listening(mock_event_system: Mock, mock_logger: Mock) -> None:
    """Test initialization with start_listening=True."""
    with patch("src.agents.base_agent.Model") as mock_model_class, \
         patch("src.agents.base_agent.TaskManager") as mock_task_manager_class:
        mock_model = AsyncMock()
        mock_model_class.return_value = mock_model
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        
        agent = TestAgent(TEST_MODEL_NAME, event_system=mock_event_system, start_listening=True)
        agent.logger = mock_logger
        
        # Verify that both health status and start tasks were created
        assert mock_task_manager.create_task.call_count == 2
        calls = mock_task_manager.create_task.call_args_list
        assert any(call.args[0].__name__ == "_update_health_status" for call in calls)
        assert any(call.args[0].__name__ == "start" for call in calls) 
