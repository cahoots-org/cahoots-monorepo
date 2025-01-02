"""Tests for the ProjectManager class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List

from src.agents.project_manager import ProjectManager
from src.services.github_service import GitHubService

@pytest.fixture
def project_manager(
    mock_event_system_singleton: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock,
    mock_github_service: Mock
) -> ProjectManager:
    """Create a ProjectManager instance with mocked dependencies."""
    manager = ProjectManager(event_system=mock_event_system_singleton)
    manager.logger = mock_base_logger
    manager.event_system = mock_event_system_singleton
    manager.model = mock_model
    manager.github_service = mock_github_service
    manager._running = False
    return manager

@pytest.fixture
def mock_github_service(mocker: "MockerFixture") -> Mock:
    """Mock the GitHub service."""
    mock = Mock()
    mock.create_issue = AsyncMock()
    mock.update_issue = AsyncMock()
    mock.get_issue = AsyncMock()
    mock.create_comment = AsyncMock()
    mocker.patch("src.agents.project_manager.GitHubService", return_value=mock)
    return mock

async def test_init_success(project_manager: ProjectManager, mock_base_logger: Mock) -> None:
    """Test successful ProjectManager initialization."""
    assert project_manager.model_name == "gpt-4"
    assert project_manager.logger == mock_base_logger
    assert mock_base_logger.debug.call_count >= 2

# ... rest of the file remains unchanged ... 