"""Tests for the UXDesigner class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List

from src.agents.ux_designer import UXDesigner
from src.services.github_service import GitHubService
from src.utils.config import Config, ServiceConfig
from src.utils.base_logger import BaseLogger

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create a mock base logger."""
    mock = Mock(spec=BaseLogger)
    mock.info = Mock()
    mock.error = Mock()
    mock.warning = Mock()
    mock.debug = Mock()
    return mock

@pytest.fixture
def mock_model() -> Mock:
    """Create a mock model."""
    mock = Mock()
    mock.generate = AsyncMock()
    mock.generate.return_value = "Test response"
    return mock

@pytest.fixture
async def ux_designer(
    mock_event_system: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock,
    mock_github_service: Mock,
    monkeypatch: pytest.MonkeyPatch
) -> UXDesigner:
    """Create a UXDesigner instance with mocked dependencies."""
    # Mock environment variables
    monkeypatch.setenv("DESIGNER_ID", "test-designer")
    
    # Mock Together API configuration
    mock_config = Config()
    mock_config.services = {
        "together": ServiceConfig(
            name="together",
            url="https://api.together.xyz",
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            api_key="test_api_key"
        )
    }
    monkeypatch.setattr("src.utils.config.config", mock_config)
    
    # Create mock github_config with design system settings
    github_config = {
        'design_system': {
            'version': '1.0',
            'model': 'gpt-4-1106-preview',
            'brand_context': {
                'primary_color': '#007bff',
                'font_family': 'Inter, system-ui, sans-serif'
            }
        }
    }
    
    # Create designer with start_listening=False to prevent automatic task creation
    designer = UXDesigner(
        event_system=mock_event_system,
        start_listening=False,
        github_service=mock_github_service,
        github_config=github_config
    )
    designer.logger = mock_base_logger
    designer.event_system = mock_event_system
    designer.model = mock_model
    designer._running = False
    
    yield designer
    
    # Cleanup
    await designer.stop()

@pytest.fixture
def mock_github_service(mocker: "MockerFixture") -> Mock:
    """Mock the GitHub service."""
    mock = Mock(spec=GitHubService)
    mock.create_issue = AsyncMock()
    mock.update_issue = AsyncMock()
    mock.get_issue = AsyncMock()
    mock.create_comment = AsyncMock()
    mocker.patch("src.agents.ux_designer.GitHubService", return_value=mock)
    return mock

@pytest.mark.asyncio
async def test_init_success(ux_designer: UXDesigner, mock_base_logger: Mock) -> None:
    """Test successful UXDesigner initialization."""
    assert ux_designer.model_name == "gpt-4-1106-preview"
    assert ux_designer.logger == mock_base_logger

@pytest.mark.asyncio
async def test_handle_story_assigned(
    ux_designer: UXDesigner,
    mock_event_system: AsyncMock,
    mock_model: Mock
) -> None:
    """Test handling of story assignment."""
    story_data = {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test description",
        "assigned_to": ux_designer.designer_id
    }
    
    # Mock the responses
    mock_design_specs = {"specs": "test specs"}
    mock_mockups = {"mockups": "test mockups"}
    
    # Mock create_design_specs and create_mockups as synchronous functions
    def mock_create_design_specs(*args, **kwargs):
        return mock_design_specs
    
    async def mock_create_mockups(*args, **kwargs):
        return mock_mockups
    
    ux_designer.create_design_specs = mock_create_design_specs
    ux_designer.create_mockups = mock_create_mockups
    
    mock_event_system.publish = AsyncMock()  # Create a new AsyncMock for publish
    
    result = await ux_designer.handle_story_assigned(story_data)
    
    assert result["status"] == "success"
    mock_event_system.publish.assert_awaited_once_with(
        "design_completed",
        {
            "story_id": story_data["story_id"],
            "designer_id": ux_designer.designer_id,
            "design_specs": mock_design_specs,
            "mockups": mock_mockups
        }
    ) 
