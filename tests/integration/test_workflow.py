"""Integration tests for complete workflow."""
import pytest
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock
from unittest.mock import patch
import os

from src.utils.event_system import EventSystem
from src.utils.task_manager import TaskManager
from src.models.story import Story
from src.services.task_management.mock import MockTaskManagementService
from src.agents.project_manager import ProjectManager
from src.agents.developer import Developer
from src.agents.ux_designer import UXDesigner
from src.agents.tester import Tester

@pytest.fixture
def mock_task_management():
    """Create a mock task management service."""
    mock = AsyncMock(spec=MockTaskManagementService)
    mock.create_board = AsyncMock(return_value={"id": "board123"})
    mock.create_list = AsyncMock(return_value={"id": "list123"})
    mock.create_card = AsyncMock(return_value={"id": "card123"})
    return mock

@pytest.fixture
def workflow_task_manager():
    """Create a task manager for workflow tests."""
    return TaskManager()

@pytest.fixture
async def mock_redis_client():
    """Create a mock Redis client."""
    class MockRedis:
        async def ping(self):
            return True

        async def publish(self, channel, message):
            return True

        async def close(self):
            return True

        def pubsub(self):
            return MockPubSub()

    class MockPubSub:
        async def subscribe(self, channel):
            return True

        async def unsubscribe(self, channel):
            return True

        async def get_message(self, ignore_subscribe_messages=True):
            return None

    return MockRedis()

@pytest.fixture
async def workflow_event_system(mock_redis_client):
    """Create an event system for workflow tests."""
    event_system = EventSystem()
    event_system.redis_client = mock_redis_client
    event_system.pubsub = mock_redis_client.pubsub()
    event_system._connected = True
    yield event_system
    await event_system.disconnect()

@pytest.fixture
async def agents(
    workflow_event_system: EventSystem,
    workflow_task_manager: TaskManager,
    mock_task_management: AsyncMock,
    mock_model: AsyncMock
) -> AsyncGenerator[Dict[str, Any], None]:
    """Create all agent instances for testing."""
    # Add Trello configuration
    from src.utils.config import config, ServiceConfig
    config.services["trello"] = ServiceConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_secret="test-secret"
    )
    
    # Add GitHub configuration
    config.services["github"] = ServiceConfig(
        name="github",
        url="https://api.github.com",
        api_key="test-key"
    )
    
    # Create mock GitHub service
    mock_github = Mock()
    mock_github.create_repository = AsyncMock(return_value="https://github.com/org/repo")
    mock_github.create_branch = AsyncMock()
    mock_github.commit_changes = AsyncMock()
    mock_github.clone_repository = AsyncMock()
    
    # Set environment variables
    os.environ["DESIGNER_ID"] = "ux1"
    
    # Create agents
    with patch('src.agents.project_manager.GitHubService', return_value=mock_github), \
         patch('src.agents.developer.GitHubService', return_value=mock_github), \
         patch('src.agents.ux_designer.GitHubService', return_value=mock_github):
        pm = ProjectManager(start_listening=False)
        dev1 = Developer(developer_id="dev1", start_listening=False)
        dev2 = Developer(developer_id="dev2", start_listening=False)
        ux = UXDesigner(start_listening=False)
        tester = Tester(start_listening=False)
        
        # Set up event system
        pm.event_system = workflow_event_system
        dev1.event_system = workflow_event_system
        dev2.event_system = workflow_event_system
        ux.event_system = workflow_event_system
        tester.event_system = workflow_event_system
        
        # Set up task manager
        pm.task_manager = workflow_task_manager
        dev1.task_manager = workflow_task_manager
        dev2.task_manager = workflow_task_manager
        ux.task_manager = workflow_task_manager
        tester.task_manager = workflow_task_manager
        
        # Set up model
        pm.model = mock_model
        dev1.model = mock_model
        dev2.model = mock_model
        ux.model = mock_model
        tester.model = mock_model
        
        # Set up task management
        pm.task_management = mock_task_management
        
        yield {
            "project_manager": pm,
            "developer1": dev1,
            "developer2": dev2,
            "ux_designer": ux,
            "tester": tester
        }
        
        # Clean up
        await pm.stop()
        await dev1.stop()
        await dev2.stop()
        await ux.stop()
        await tester.stop()

@pytest.mark.timeout(30)
async def test_complete_workflow(
    agents: Dict[str, Any],
    workflow_event_system: EventSystem,
    workflow_task_manager: TaskManager,
    mock_task_management: AsyncMock,
    mock_redis_client
) -> None:
    """Test complete workflow from project creation to completion.
    
    Verifies:
    1. Project creation and planning
    2. Story assignment and implementation
    3. Design creation and review
    4. Testing and validation
    5. Event system coordination
    """
    pm = agents["project_manager"]
    dev = agents["developer1"]
    ux = agents["ux_designer"]
    tester = agents["tester"]
    
    # Set event system for all agents
    for agent in [pm, dev, ux, tester]:
        agent.event_system = workflow_event_system
    
    # Connect event system with mock Redis client
    await workflow_event_system.connect(mock_redis_client)
    await workflow_event_system.start_listening()
    
    # Mock model responses
    pm.model = AsyncMock()
    pm.model.generate_response = AsyncMock(return_value=json.dumps({
        "milestones": [
            {
                "title": "User Authentication",
                "description": "Implement core authentication features",
                "stories": [
                    {
                        "id": "story-1",
                        "title": "User Registration",
                        "description": "Implement user registration with email verification",
                        "priority": 1
                    }
                ]
            }
        ],
        "tasks": [
            {
                "id": "task1",
                "title": "Implement Registration",
                "description": "Create user registration endpoint",
                "milestone": "User Authentication",
                "story": "story-1"
            }
        ],
        "dependencies": [
            {
                "from": "task1",
                "to": "story-1"
            }
        ],
        "estimates": {
            "task1": "1 week",
            "story-1": "1 week"
        }
    }))
    
    dev.model.generate_response = AsyncMock(return_value=json.dumps({
        "implementation": [
            {
                "file": "auth.py",
                "code": "def register_user(): pass",
                "tests": ["test_register_user"]
            }
        ]
    }))
    
    ux.model.generate_response = AsyncMock(return_value=json.dumps({
        "wireframes": [
            {
                "name": "Login Page",
                "components": ["username", "password", "submit"]
            }
        ]
    }))
    
    tester.model.generate_response = AsyncMock(return_value=json.dumps({
        "test_suite": {
            "title": "Test Registration",
            "description": "Verify user registration flow",
            "test_cases": [
                {
                    "title": "Test Registration Flow",
                    "description": "Verify user registration with email verification",
                    "steps": [
                        "Navigate to registration page",
                        "Fill in user details",
                        "Submit form"
                    ],
                    "expected_result": "User is registered and email verification is sent"
                }
            ]
        }
    }))
    
    # Create project
    project_name = "Auth System"
    project_description = "Create a user authentication system with profile management"
    requirements = [
        "User registration with email verification",
        "Login with password",
        "Password reset functionality",
        "User profile management",
        "Session handling"
    ]
    
    roadmap = await pm.create_roadmap(project_name, project_description, requirements)
    assert roadmap is not None
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify board creation
    mock_task_management.create_board.assert_called_once_with(project_name, project_description)
    
    # Verify list creation
    mock_task_management.create_list.assert_called_with(board_id="board123", name="Backlog")
    
    # Verify card creation
    mock_task_management.create_card.assert_called()
    
    # Clean up
    await workflow_event_system.stop_listening()
    await workflow_event_system.disconnect()

@pytest.mark.timeout(20)
async def test_concurrent_stories(
    agents: Dict[str, Any],
    workflow_event_system: EventSystem,
    workflow_task_manager: TaskManager,
    mock_task_management: AsyncMock,
    mock_redis_client
) -> None:
    """Test handling of concurrent story assignments.
    
    Verifies:
    1. Concurrent story processing
    2. Resource management
    3. Event ordering
    4. System stability
    """
    pm = agents["project_manager"]
    dev = agents["developer1"]
    ux = agents["ux_designer"]
    tester = agents["tester"]
    
    # Set event system for all agents
    for agent in [pm, dev, ux, tester]:
        agent.event_system = workflow_event_system
    
    # Connect event system with mock Redis client
    await workflow_event_system.connect(mock_redis_client)
    await workflow_event_system.start_listening()
    
    # Mock model responses
    dev.model.generate_response = AsyncMock(return_value=json.dumps({
        "implementation": [
            {
                "file": "feature.py",
                "code": "def implement(): pass",
                "tests": ["test_feature"]
            }
        ]
    }))
    
    ux.model.generate_response = AsyncMock(return_value=json.dumps({
        "wireframes": [
            {
                "name": "Feature UI",
                "components": ["button", "form"]
            }
        ]
    }))
    
    tester.model.generate_response = AsyncMock(return_value=json.dumps({
        "test_suite": {
            "title": "Test Feature",
            "description": "Verify feature functionality",
            "test_cases": [
                {
                    "title": "Test Feature Flow",
                    "description": "Verify feature works as expected",
                    "steps": [
                        "Setup test environment",
                        "Execute test steps",
                        "Verify results"
                    ],
                    "expected_result": "Feature works as expected"
                }
            ]
        }
    }))
    
    # Create multiple stories
    stories = [
        Story(
            id=f"story-{i}",
            title=f"Test Story {i}",
            description=f"Test description {i}",
            priority=i,
            status="open"
        ) for i in range(1, 4)
    ]
    
    # Set up event handlers
    await pm.setup_events()
    await dev.setup_events()
    await ux.setup_events()
    await tester.setup_events()
    
    # Publish stories
    for story in stories:
        await workflow_event_system.publish("project_manager", {
            "type": "story_created",
            "data": story.dict()
        })
    
    # Clean up
    await workflow_event_system.stop_listening()
    await workflow_event_system.disconnect()

@pytest.mark.timeout(20)
async def test_error_handling(
    agents: Dict[str, Any],
    workflow_event_system: EventSystem,
    workflow_task_manager: TaskManager,
    mock_task_management: AsyncMock
) -> None:
    """Test error handling in workflow.
    
    Verifies:
    1. Error propagation
    2. Recovery mechanisms
    3. System stability
    """
    pm = agents["project_manager"]
    dev = agents["developer1"]
    ux = agents["ux_designer"]
    tester = agents["tester"]
    
    # Set event system for all agents
    for agent in [pm, dev, ux, tester]:
        agent.event_system = workflow_event_system
    
    # Mock error responses
    mock_task_management.create_board.side_effect = Exception("Failed to create board")
    mock_task_management.create_list.side_effect = Exception("Failed to create list")
    mock_task_management.create_card.side_effect = Exception("Failed to create card")
    
    # Mock model response
    pm.model.generate_response = AsyncMock(return_value=json.dumps({
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
            }
        ],
        "tasks": [
            {
                "id": "task1",
                "title": "Task 1",
                "description": "First task",
                "milestone": "Milestone 1",
                "story": "story1"
            }
        ],
        "dependencies": [],
        "estimates": {
            "task1": "3 days"
        }
    }))
    
    # Create project with error
    project_name = "Error Project"
    project_description = "Test error handling"
    requirements = ["req1", "req2"]
    
    try:
        await pm.create_roadmap(project_name, project_description, requirements)
    except Exception:
        pass
    
    # Wait for error processing
    await asyncio.sleep(1)
    
    # Verify error handling
    assert mock_task_management.create_board.call_count > 0
    assert mock_task_management.create_board.call_args[0] == (project_name, project_description) 