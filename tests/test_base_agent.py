"""Tests for the BaseAgent class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger
from src.utils.model import Model

class TestAgent(BaseAgent):
    """Concrete test implementation of BaseAgent."""
    
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages."""
        self.logger.info(f"Test agent received system message: {message}")
        
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment."""
        return {
            "status": "success",
            "data": {"message": "Story handled by test agent"}
        }

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
def mock_model():
    """Create a mock model."""
    mock = AsyncMock()
    mock.generate_response.return_value = "Test response"
    return mock

@pytest.fixture
async def base_agent(mock_event_system, mock_logger, mock_model):
    """Create a base agent instance."""
    with patch("src.agents.base_agent.Model", return_value=mock_model):
        agent = TestAgent("test_model", event_system=mock_event_system)
        agent.logger = mock_logger
        yield agent
        await agent.stop()

@pytest.mark.asyncio
async def test_init_success(mock_event_system, mock_logger):
    """Test successful agent initialization."""
    with patch("src.agents.base_agent.Model") as mock_model_class:
        mock_model = AsyncMock()
        mock_model_class.return_value = mock_model
        
        agent = TestAgent("test_model", event_system=mock_event_system)
        agent.logger = mock_logger
        
        assert agent.model_name == "test_model"
        assert agent.event_system == mock_event_system
        assert agent.logger == mock_logger
        
@pytest.mark.asyncio
async def test_init_failure(mock_event_system, mock_logger):
    """Test agent initialization failure."""
    with patch("src.agents.base_agent.Model", side_effect=Exception("Test error")):
        with pytest.raises(Exception, match="Test error"):
            agent = TestAgent("test_model", event_system=mock_event_system)

@pytest.mark.asyncio
async def test_setup_events(base_agent):
    """Test event setup."""
    await base_agent.setup_events()
    
    # Verify default handlers are registered
    assert "system" in base_agent.event_handler._handlers
    assert "story_assigned" in base_agent.event_handler._handlers

@pytest.mark.asyncio
async def test_start_stop(base_agent, mock_event_system):
    """Test starting and stopping the agent."""
    # Start agent
    await base_agent.start()
    assert base_agent.event_handler._listening is True
    
    # Stop agent
    await base_agent.stop()
    assert base_agent.event_handler._listening is False

@pytest.mark.asyncio
async def test_managed_operation(base_agent):
    """Test managed operation context manager."""
    async with base_agent.managed_operation():
        assert base_agent.event_handler._listening is True
    
    assert base_agent.event_handler._listening is False

@pytest.mark.asyncio
async def test_handle_system_message(base_agent):
    """Test system message handling."""
    message = {"type": "system", "command": "test"}
    await base_agent.handle_system_message(message)
    # Base implementation should not raise any errors

@pytest.mark.asyncio
async def test_handle_story_assigned(base_agent):
    """Test story assignment handling."""
    message = {
        "type": "story_assigned",
        "story_id": "test123",
        "title": "Test Story"
    }
    await base_agent.handle_story_assigned(message)
    # Base implementation should not raise any errors 