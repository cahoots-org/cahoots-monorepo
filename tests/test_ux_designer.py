"""Tests for the UXDesigner class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List

from src.agents.ux_designer import UXDesigner
from src.services.github_service import GitHubService

@pytest.fixture
def ux_designer(
    mock_event_system_singleton: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock,
    mock_github_service: Mock
) -> UXDesigner:
    """Create a UXDesigner instance with mocked dependencies."""
    designer = UXDesigner(event_system=mock_event_system_singleton)
    designer.logger = mock_base_logger
    designer.event_system = mock_event_system_singleton
    designer.model = mock_model
    designer.github_service = mock_github_service
    designer._running = False
    return designer

@pytest.fixture
def mock_github_service(mocker: "MockerFixture") -> Mock:
    """Mock the GitHub service."""
    mock = Mock()
    mock.create_issue = AsyncMock()
    mock.update_issue = AsyncMock()
    mock.get_issue = AsyncMock()
    mock.create_comment = AsyncMock()
    mocker.patch("src.agents.ux_designer.GitHubService", return_value=mock)
    return mock

async def test_init_success(ux_designer: UXDesigner, mock_base_logger: Mock) -> None:
    """Test successful UXDesigner initialization."""
    assert ux_designer.model_name == "gpt-4"
    assert ux_designer.logger == mock_base_logger
    assert mock_base_logger.debug.call_count >= 2 