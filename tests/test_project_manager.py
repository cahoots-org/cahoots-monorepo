"""Tests for the project manager agent.

This module contains tests for the ProjectManager class, which handles:
- Project creation and setup
- Story management
- Roadmap generation
- Task tracking
"""
from datetime import datetime
from typing import Any, Dict, List, AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
import json
import os

import pytest
from pytest_mock import MockFixture

from src.agents.project_manager import ProjectManager
from src.core.messaging.messages import SystemMessage
from src.models.story import Story
from src.utils.model import Model
from src.utils.base_logger import BaseLogger
from src.services.trello.config import TrelloConfig

# Test constants
TEST_PROJECT_ID = "proj123"
TEST_PROJECT_NAME = "Test Project"
TEST_PROJECT_DESC = "A test project"
TEST_STORY_ID = "story123"
TEST_BOARD_ID = "board123"
TEST_LIST_ID = "list123"
TEST_CARD_ID = "card123"

# Test data
TEST_PROJECT_MESSAGE = SystemMessage(
    command="project_created",
    payload={
        "project_id": TEST_PROJECT_ID,
        "name": TEST_PROJECT_NAME,
        "description": TEST_PROJECT_DESC
    }
)

TEST_STORY_MESSAGE = SystemMessage(
    command="story_created",
    payload={
        "story_id": TEST_STORY_ID,
        "project_id": TEST_PROJECT_ID,
        "title": "New Story",
        "description": "A new story",
        "priority": 1
    }
)

TEST_ROADMAP_RESPONSE = {
    "milestones": [
        {
            "title": "Milestone 1",
            "description": "First milestone",
            "stories": [
                {
                    "id": "story1",
                    "title": "Story 1",
                    "description": "First story",
                    "priority": 1,
                    "status": "open"
                }
            ],
            "dependencies": [],
            "estimate": "1 week"
        },
        {
            "title": "Milestone 2",
            "description": "Second milestone",
            "stories": [
                {
                    "id": "story2",
                    "title": "Story 2",
                    "description": "Second story",
                    "priority": 2,
                    "status": "open"
                }
            ],
            "dependencies": [],
            "estimate": "2 weeks"
        }
    ],
    "tasks": [
        {
            "id": "task1",
            "title": "Task 1",
            "description": "First task",
            "milestone": "Milestone 1",
            "story": "story1"
        },
        {
            "id": "task2",
            "title": "Task 2",
            "description": "Second task",
            "milestone": "Milestone 2",
            "story": "story2"
        }
    ],
    "dependencies": [
        {
            "from": "task1",
            "to": "task2"
        }
    ],
    "estimates": {
        "task1": "3 days",
        "task2": "5 days"
    }
}

@pytest.fixture
def mock_task_management() -> AsyncMock:
    """Create mock task management service for testing.
    
    Returns:
        AsyncMock: Configured task management mock with required methods.
    """
    mock = AsyncMock()
    mock.create_board = AsyncMock(return_value={"id": TEST_BOARD_ID})
    mock.create_list = AsyncMock(return_value={"id": TEST_LIST_ID})
    mock.create_card = AsyncMock(return_value={"id": TEST_CARD_ID})
    return mock

@pytest.fixture
def mock_github_service() -> AsyncMock:
    """Create mock GitHub service for testing.
    
    Returns:
        AsyncMock: Configured GitHub service mock with required methods.
    """
    mock = Mock()
    mock.create_repository = AsyncMock(return_value="https://github.com/org/repo")
    mock.create_branch = AsyncMock()
    mock.commit_changes = AsyncMock()
    mock.clone_repository = AsyncMock()
    return mock

@pytest.fixture
def mock_model() -> AsyncMock:
    """Create mock model for testing.
    
    Returns:
        AsyncMock: Model mock with generate_response method.
    """
    mock = AsyncMock(spec=Model)
    mock.generate_response = AsyncMock()
    return mock

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create mock logger for testing.
    
    Returns:
        Mock: Logger mock with standard logging methods.
    """
    mock = Mock(spec=BaseLogger)
    mock.error = Mock()
    mock.info = Mock()
    mock.debug = Mock()
    mock.warning = Mock()
    return mock

@pytest.fixture
def mock_env() -> AsyncGenerator[None, None]:
    """Mock environment variables for testing.
    
    Yields:
        None
    """
    with patch.dict(os.environ, {
        "TRELLO_API_KEY": "test-key",
        "TRELLO_API_TOKEN": "test-token",
        "TRELLO_API_SECRET": "test-secret"
    }):
        yield

@pytest.fixture
async def project_manager(
    mock_task_management: AsyncMock,
    mock_model: AsyncMock,
    mock_event_system: AsyncMock,
    mock_base_logger: Mock,
    mock_github_service: AsyncMock,
    mock_env: None
) -> AsyncGenerator[ProjectManager, None]:
    """Create project manager instance for testing.
    
    Args:
        mock_task_management: Task management service mock
        mock_model: Model mock
        mock_event_system: Event system mock
        mock_base_logger: Logger mock
        mock_github_service: GitHub service mock
        mock_env: Environment variables mock
    
    Yields:
        ProjectManager: Configured project manager instance.
    """
    with patch('src.agents.project_manager.GitHubService', return_value=mock_github_service):
        pm = ProjectManager(start_listening=False)
    
    # Configure mocks
    pm.task_management = mock_task_management
    pm.model = mock_model
    pm.event_system = mock_event_system
    pm.logger = mock_base_logger
    
    # Mock Redis for health status updates
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_event_system.redis = mock_redis
    
    yield pm
    
    # Cleanup
    if hasattr(pm, '_task_manager'):
        await pm._task_manager.cancel_all()

class TestProjectManager:
    """Tests for the ProjectManager class."""
    
    @pytest.mark.asyncio
    async def test_handle_project_created(
        self,
        project_manager: ProjectManager,
        mock_task_management: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling project creation event."""
        # Setup
        await project_manager.setup_events()
        
        # Execute
        await project_manager.handle_system_message(TEST_PROJECT_MESSAGE)
        
        # Verify board creation
        mock_task_management.create_board.assert_called_once_with(
            name=TEST_PROJECT_NAME,
            description=TEST_PROJECT_DESC
        )
        
        # Verify list creation
        mock_task_management.create_list.assert_called_once_with(
            board_id=TEST_BOARD_ID,
            name="Backlog"
        )
    
    @pytest.mark.asyncio
    async def test_handle_story_created(
        self,
        project_manager: ProjectManager,
        mock_task_management: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling story creation event."""
        # Setup
        await project_manager.setup_events()
        await project_manager.handle_system_message(TEST_PROJECT_MESSAGE)
        
        # Execute
        await project_manager.handle_system_message(TEST_STORY_MESSAGE)
        
        # Verify card creation
        mock_task_management.create_card.assert_called_once_with(
            list_id=TEST_LIST_ID,
            name="New Story",
            description="A new story",
            position=1
        )
    
    @pytest.mark.asyncio
    async def test_handle_invalid_command(
        self,
        project_manager: ProjectManager,
        mock_task_management: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling invalid command."""
        # Setup
        await project_manager.setup_events()
        invalid_message = SystemMessage(command="invalid_command", payload={})
        
        # Execute
        await project_manager.handle_system_message(invalid_message)
        
        # Verify no actions taken
        mock_task_management.create_board.assert_not_called()
        mock_task_management.create_list.assert_not_called()
        mock_task_management.create_card.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_roadmap(
        self,
        mock_model: AsyncMock,
        mock_task_management: AsyncMock,
        mock_event_system: AsyncMock,
        mock_base_logger: Mock,
        mock_github_service: AsyncMock,
        mock_env: None
    ) -> None:
        """Test roadmap creation with milestones and tasks."""
        # Setup
        requirements = ["req1", "req2"]
        mock_model.generate_response = AsyncMock(
            return_value=json.dumps(TEST_ROADMAP_RESPONSE)
        )
        
        # Mock Redis for health status updates
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_event_system.redis = mock_redis
        
        # Create project manager
        with patch('src.agents.project_manager.GitHubService', return_value=mock_github_service):
            pm = ProjectManager(start_listening=False)
        
        pm.task_management = mock_task_management
        pm.model = mock_model
        pm.event_system = mock_event_system
        pm.logger = mock_base_logger
        
        # Execute
        roadmap = await pm.create_roadmap(
            TEST_PROJECT_NAME,
            TEST_PROJECT_DESC,
            requirements
        )
        
        # Verify roadmap structure
        assert len(roadmap["milestones"]) == 2
        assert len(roadmap["tasks"]) == 2
        assert len(roadmap["dependencies"]) == 1
        
        # Verify model was called with correct prompt
        mock_model.generate_response.assert_called_once()
        prompt = mock_model.generate_response.call_args[0][0]
        assert TEST_PROJECT_NAME in prompt
        assert TEST_PROJECT_DESC in prompt
        assert all(req in prompt for req in requirements) 