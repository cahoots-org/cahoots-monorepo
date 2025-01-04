"""Tests for project manager agent."""
import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.agents.project_manager import ProjectManager
from src.core.messaging.messages import SystemMessage
from src.models.story import Story

@pytest.fixture
def mock_task_management():
    """Create mock task management service."""
    mock = AsyncMock()
    mock.create_board = AsyncMock(return_value={"id": "board123"})
    mock.create_list = AsyncMock(return_value={"id": "list123"})
    mock.create_card = AsyncMock(return_value={"id": "card123"})
    return mock

@pytest.fixture
def mock_github_service():
    """Create mock GitHub service."""
    mock = Mock()
    mock.create_repository = AsyncMock(return_value="https://github.com/org/repo")
    mock.create_branch = AsyncMock()
    mock.commit_changes = AsyncMock()
    mock.clone_repository = AsyncMock()
    return mock

@pytest.fixture
def project_manager(mock_task_management, mock_model, mock_event_system, mock_base_logger, mock_github_service):
    """Create project manager instance."""
    # Add Trello configuration
    from src.utils.config import config, ServiceConfig
    config.services["trello"] = ServiceConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_secret="test-secret"
    )
    
    with patch('src.agents.project_manager.GitHubService', return_value=mock_github_service):
        pm = ProjectManager(start_listening=False)
    pm.task_management = mock_task_management
    pm.model = mock_model
    pm.event_system = mock_event_system
    pm.logger = mock_base_logger
    return pm

@pytest.mark.asyncio
async def test_handle_project_created(project_manager, mock_task_management, mock_base_logger):
    """Test handling project creation event."""
    # Set up event handler
    await project_manager.setup_events()
    
    message = SystemMessage(
        command="project_created",
        payload={
            "project_id": "proj123",
            "name": "Test Project",
            "description": "A test project"
        }
    )
    
    await project_manager.handle_system_message(message)
    
    # Verify board creation
    mock_task_management.create_board.assert_called_once_with(
        name="Test Project",
        description="A test project"
    )
    
    # Verify list creation
    mock_task_management.create_list.assert_called_once_with(
        board_id="board123",
        name="Backlog"
    )

@pytest.mark.asyncio
async def test_handle_story_created(project_manager, mock_task_management, mock_base_logger):
    """Test handling story creation event."""
    # Set up event handler
    await project_manager.setup_events()
    
    message = SystemMessage(
        command="story_created",
        payload={
            "story_id": "story123",
            "project_id": "proj123",
            "title": "New Story",
            "description": "A new story",
            "priority": 1
        }
    )
    
    await project_manager.handle_system_message(message)
    
    # Verify card creation
    mock_task_management.create_card.assert_called_once_with(
        list_id="list123",
        name="New Story",
        description="A new story",
        position=1
    )

@pytest.mark.asyncio
async def test_handle_invalid_command(project_manager, mock_task_management, mock_base_logger):
    """Test handling invalid command."""
    # Set up event handler
    await project_manager.setup_events()
    
    message = SystemMessage(
        command="invalid_command",
        payload={}
    )
    
    await project_manager.handle_system_message(message)
    
    # Verify no actions taken
    mock_task_management.create_board.assert_not_called()
    mock_task_management.create_list.assert_not_called()
    mock_task_management.create_card.assert_not_called()

@pytest.mark.asyncio
async def test_create_roadmap(mock_model, mock_task_management, mock_event_system, mock_base_logger, mock_github_service):
    """Test roadmap creation."""
    project_name = "Test Project"
    project_description = "A test project"
    requirements = ["req1", "req2"]
    
    # Mock model response
    mock_model.generate_response = AsyncMock(return_value=json.dumps({
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
    }))

    # Mock task management responses
    mock_task_management.create_board = AsyncMock(return_value={"id": "board123"})
    mock_task_management.create_list = AsyncMock(return_value={"id": "list123"})
    
    # Add Trello configuration
    from src.utils.config import config, ServiceConfig
    config.services["trello"] = ServiceConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_secret="test-secret"
    )
    
    # Create project manager
    with patch('src.agents.project_manager.GitHubService', return_value=mock_github_service):
        pm = ProjectManager(start_listening=False)
    pm.task_management = mock_task_management
    pm.model = mock_model
    pm.event_system = mock_event_system
    pm.logger = mock_base_logger
    
    # Create roadmap
    roadmap = await pm.create_roadmap(project_name, project_description, requirements)
    
    # Verify roadmap created
    assert roadmap is not None
    assert len(roadmap["milestones"]) == 2
    assert roadmap["milestones"][0]["stories"][0]["priority"] == 1
    assert roadmap["milestones"][1]["stories"][0]["priority"] == 2 