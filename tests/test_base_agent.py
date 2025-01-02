"""Tests for the BaseAgent class."""
import pytest
from unittest.mock import Mock, AsyncMock, call, patch
from pytest_mock import MockerFixture
import logging
from typing import Any, Dict, List

from src.agents.base_agent import BaseAgent
from src.utils.model import Model
from src.utils.base_logger import BaseLogger

class TestAgent(BaseAgent):
    """Test agent implementation."""
    def __init__(self, model_name: str = "test-model", event_system=None) -> None:
        """Initialize test agent."""
        super().__init__(model_name, start_listening=False, event_system=event_system)

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle test message."""
        pass

@pytest.fixture
def test_agent(
    mock_event_system_singleton: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock
) -> TestAgent:
    """Create a test agent instance."""
    agent = TestAgent(event_system=mock_event_system_singleton)
    agent.logger = mock_base_logger
    agent.event_system = mock_event_system_singleton
    agent.model = mock_model
    agent._running = False
    return agent

@pytest.fixture
def mock_model(mocker: "MockerFixture") -> Mock:
    """Mock the model."""
    mock = Mock()
    mock.generate_response = AsyncMock(return_value="Test response")
    mocker.patch("src.agents.base_agent.Model", return_value=mock)
    return mock

async def test_init_success(test_agent: TestAgent, mock_base_logger: Mock) -> None:
    """Test successful agent initialization."""
    assert test_agent.model_name == "test-model"
    assert test_agent.logger == mock_base_logger
    assert mock_base_logger.debug.call_count >= 2

async def test_init_failure(
    mock_event_system: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test handling of initialization failure."""
    # Mock Model to raise an exception
    mocker.patch(
        "src.agents.base_agent.Model",
        side_effect=Exception("Model initialization failed")
    )

    # Verify initialization failure
    with pytest.raises(Exception) as exc_info:
        TestAgent(model_name="test-model")

    assert "Model initialization failed" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        call("Failed to initialize TestAgent: Model initialization failed"),
        call("Stack trace:", exc_info=True)
    ])

async def test_generate_response(
    agent: TestAgent,
    mock_model: Mock
) -> None:
    """Test response generation."""
    response = await agent.generate_response("test prompt")
    assert response == "Test response"
    mock_model.generate_response.assert_called_once_with("test prompt") 