"""Unit tests for the DeveloperAgent class."""
from typing import TYPE_CHECKING, Dict, Any, List
import pytest
from unittest.mock import AsyncMock, Mock, patch
import json
import uuid
import asyncio
from asyncio import TaskGroup

from agent_developer.agent import DeveloperAgent
from core.models import Task
from core.utils.event_system import EventSystem
from core.services.github_service import GitHubService
from core.utils.task_manager import TaskManager

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from _pytest.logging import LogCaptureFixture
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.monkeypatch import MonkeyPatch

# Set timeout for all tests in this module
pytestmark = pytest.mark.timeout(5)

# Configure pytest-asyncio to use auto mode
pytest.mark.asyncio.mode = "auto"

@pytest.fixture(autouse=True)
async def cleanup_event_loop():
    """Clean up any pending tasks in the event loop after each test."""
    yield
    # Get all tasks from the event loop
    loop = asyncio.get_event_loop()
    pending_tasks = [task for task in asyncio.all_tasks(loop) 
                    if not task.done() and task != asyncio.current_task()]
    
    if pending_tasks:
        # Cancel all pending tasks
        for task in pending_tasks:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

@pytest.fixture
def mock_task_manager() -> Mock:
    """Create a mock task manager."""
    mock = Mock()
    mock.break_down_story = AsyncMock()
    mock.cleanup = AsyncMock()
    mock.running = True
    return mock

@pytest.fixture
def mock_github_service() -> Mock:
    """Create a mock GitHub service."""
    mock = Mock()
    mock.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    mock.create_branch = AsyncMock()
    mock.commit_changes = AsyncMock()
    mock.clone_repository = AsyncMock()
    mock.create_review_comment = AsyncMock()
    return mock

@pytest.fixture
def mock_code_generator() -> Mock:
    """Create a mock code generator."""
    mock = Mock()
    mock.generate_implementation = AsyncMock(return_value={
        "code": "def test():\n    pass",
        "file_path": "src/test.py"
    })
    return mock

@pytest.fixture
def mock_code_validator() -> Mock:
    """Create a mock code validator."""
    mock = Mock()
    mock.validate_implementation = AsyncMock(return_value={
        "valid": True,
        "errors": []
    })
    return mock

@pytest.fixture
def mock_feedback_manager() -> Mock:
    """Create a mock feedback manager."""
    mock = Mock()
    mock.get_relevant_feedback = Mock(return_value=[])
    mock.integrate_feedback = Mock()
    return mock

@pytest.fixture
def mock_file_manager() -> Mock:
    """Create a mock file manager."""
    mock = Mock()
    mock.determine_file_path = Mock(side_effect=lambda task: {
        "Create User Model": "src/models/user.py",
        "Implement API Endpoint": "src/api/endpoint.py",
        "Create UI Component": "src/ui/component.py",
        "Write Tests": "tests/test_component.py",
        "Generic Task": "src/core/module.py"
    }[task.title])
    return mock

@pytest.fixture
def mock_pr_manager() -> Mock:
    """Create a mock PR manager."""
    mock = Mock()
    mock.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    return mock

@pytest.fixture
def mock_event_system() -> AsyncMock:
    """Create a mock event system."""
    mock = AsyncMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.connect = AsyncMock()
    mock._connected = True  # Internal state
    mock.is_connected = False  # Direct property instead of using property()
    mock.disconnect = AsyncMock()
    return mock

@pytest.fixture
def mock_tasks() -> List[Task]:
    """Create a list of mock tasks."""
    return [
        Task(
            id=str(uuid.uuid4()),
            title="Create User Model",
            description="Create a user model with basic fields",
            requires_ux=False,
            metadata={}
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Implement API Endpoint",
            description="Create an API endpoint for user management",
            requires_ux=False,
            metadata={}
        )
    ]

@pytest.fixture
def mock_implementation() -> Dict[str, Any]:
    """Create a mock implementation result."""
    return {
        "code": "def test():\n    pass",
        "file_path": "src/test.py",
        "validation": {"valid": True, "errors": []}
    }

@pytest.fixture
def mock_task() -> Task:
    """Create a single mock task."""
    return Task(
        id=str(uuid.uuid4()),
        title="Create User Model",
        description="Create a user model with basic fields",
        requires_ux=False,
        metadata={}
    )

@pytest.fixture
async def developer(
    mock_event_system: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock,
    mock_github_service: Mock,
    mock_task_manager: Mock,
    mock_code_generator: Mock,
    mock_code_validator: Mock,
    mock_feedback_manager: Mock,
    mock_file_manager: Mock,
    mock_pr_manager: Mock,
    monkeypatch: pytest.MonkeyPatch
) -> DeveloperAgent:
    """Create a Developer instance with mocked dependencies."""
    # Mock environment variables
    monkeypatch.setenv("DEVELOPER_ID", "test-developer")
    
    # Create developer with start_listening=False to prevent automatic task creation
    developer = DeveloperAgent(
        event_system=mock_event_system,
        start_listening=False,
        github_service=mock_github_service
    )
    
    # Configure mocks
    developer.logger = mock_base_logger
    developer.event_system = mock_event_system
    developer.model = mock_model
    developer.task_manager = mock_task_manager
    developer.code_generator = mock_code_generator
    developer.code_validator = mock_code_validator
    developer.feedback_manager = mock_feedback_manager
    developer.file_manager = mock_file_manager
    developer.pr_manager = mock_pr_manager
    
    await developer.start()
    return developer

@pytest.mark.asyncio
async def test_setup_events(
    developer: DeveloperAgent,
    mock_event_system: Mock
) -> None:
    """Test event system setup."""
    # Set is_connected to False to trigger connect
    mock_event_system._connected = False
    mock_event_system.subscribe = AsyncMock()

    await developer.start()  # This will handle setup_events internally

    # Verify event system setup
    mock_event_system.connect.assert_awaited_once()
    assert mock_event_system.subscribe.await_count >= 3  # Should subscribe to multiple channels

@pytest.mark.asyncio
async def test_handle_task_assigned(
    developer: DeveloperAgent,
    mock_task: Task,
    mock_implementation: Dict[str, Any],
    mock_code_generator: Mock,
    mock_code_validator: Mock,
    mock_pr_manager: Mock
) -> None:
    """Test handling of task assignment."""
    # Test data
    task_data = {
        "task_id": mock_task.id,
        "title": mock_task.title,
        "description": mock_task.description,
        "assigned_to": developer.developer_id
    }
    
    # Configure mocks
    mock_code_generator.generate_implementation.return_value = mock_implementation
    mock_code_validator.validate_implementation.return_value = {"valid": True, "errors": []}
    mock_pr_manager.create_pr.return_value = "https://github.com/org/repo/pull/1"
    
    # Execute
    result = await developer.handle_task_assigned(task_data)
    
    # Verify
    assert result["status"] == "success"
    assert "data" in result
    assert "implementations" in result["data"]
    assert mock_task.id in result["data"]["implementations"]
    assert result["data"]["pr_url"] == "https://github.com/org/repo/pull/1"

@pytest.mark.asyncio
async def test_handle_story_assigned(
    developer: DeveloperAgent,
    mock_event_system: Mock,
    mock_github_service: Mock,
    mock_task_manager: Mock,
    mock_tasks: List[Task]
) -> None:
    """Test story assignment handling."""
    # Test data
    story_data = {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test story description",
        "repo_url": "https://github.com/org/repo",
        "assigned_to": developer.developer_id
    }
    
    message = {
        "type": "story_assigned",
        "story": story_data
    }
    
    # Configure mocks
    mock_task_manager.break_down_story.return_value = mock_tasks
    developer.implement_tasks = AsyncMock(return_value={
        "implementations": {
            mock_tasks[0].id: {
                "code": "def test():\n    pass",
                "file_path": "src/test.py",
                "task": mock_tasks[0].model_dump()
            }
        },
        "failed_tasks": []
    })
    developer.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    
    # Test normal case
    result = await developer.handle_story_assigned(message)
    assert result["status"] == "success"
    assert result["pr_url"] == "https://github.com/org/repo/pull/1"
    
    # Verify event system interactions
    mock_event_system.publish.assert_any_await("implementation_started", {
        "story_id": "story-1",
        "developer_id": developer.developer_id
    })
    mock_event_system.publish.assert_any_await("implementation_completed", {
        "story_id": "story-1",
        "developer_id": developer.developer_id,
        "pr_url": "https://github.com/org/repo/pull/1"
    })
    
    # Verify GitHub service interactions
    mock_github_service.clone_repository.assert_awaited_once_with(story_data["repo_url"])

@pytest.mark.asyncio
async def test_handle_review_request(
    developer: DeveloperAgent,
    mock_github_service: Mock
) -> None:
    """Test handling of review request."""
    # Test data
    pr_data = {
        "pr_id": "pr-1",
        "pr_url": "https://github.com/org/repo/pull/1",
        "files": {
            "src/test.py": "def test():\n    pass"
        }
    }
    
    # Execute
    result = await developer.handle_review_request(pr_data)
    
    # Verify
    assert result["status"] == "success"
    assert "comments" in result
    assert "suggestions" in result
    assert "critical_issues" in result
    assert "approved" in result
    mock_github_service.create_review_comment.assert_awaited_once()

@pytest.mark.asyncio
async def test_implement_tasks_success(
    developer: DeveloperAgent,
    mock_tasks: List[Task],
    mock_implementation: Dict[str, Any],
    caplog: "LogCaptureFixture"
) -> None:
    """Test successful implementation of multiple tasks."""
    # Mock code generator
    developer.code_generator.generate_implementation.return_value = mock_implementation
    
    # Mock code validator
    developer.code_validator.validate_implementation.return_value = {
        "valid": True,
        "errors": []
    }

    # Call implement_tasks
    result = await developer.implement_tasks(mock_tasks)

    # Verify successful implementations
    assert "implementations" in result
    assert "failed_tasks" in result
    assert len(result["implementations"]) == 2
    assert len(result["failed_tasks"]) == 0

    # Verify implementation details
    for task_id, implementation in result["implementations"].items():
        assert "code" in implementation
        assert "file_path" in implementation
        assert "task" in implementation
        assert implementation["code"] == mock_implementation["code"]
        assert implementation["file_path"] == mock_implementation["file_path"]

    # Verify logging
    assert "Failed to implement task" not in caplog.text

@pytest.mark.asyncio
async def test_implement_tasks_partial_failure(
    developer: DeveloperAgent,
    mock_tasks: List[Task],
    mock_implementation: Dict[str, Any],
    caplog: "LogCaptureFixture"
) -> None:
    """Test task implementation with some failures."""
    # Configure mocks to fail for second task
    developer.code_generator.generate_implementation.side_effect = [
        mock_implementation,
        Exception("Failed to generate implementation")
    ]
    
    # Execute
    result = await developer.implement_tasks(mock_tasks)
    
    # Verify
    assert len(result["implementations"]) == 1
    assert len(result["failed_tasks"]) == 1
    
    # Verify successful implementation
    task_id = list(result["implementations"].keys())[0]
    assert result["implementations"][task_id]["code"] == mock_implementation["code"]
    
    # Verify failed task
    assert result["failed_tasks"][0]["error"] == "Failed to generate implementation"

@pytest.mark.asyncio
async def test_needs_ux_design(
    developer: DeveloperAgent,
    mock_tasks: List[Task]
) -> None:
    """Test UX design requirement detection."""
    # Test with non-UX tasks
    assert not developer.needs_ux_design(mock_tasks)
    
    # Test with UX task
    ux_task = Task(
        id="task-3",
        title="UX Task",
        description="UX task description",
        requires_ux=True,
        metadata={
            "type": "implementation",
            "complexity": 1,
            "dependencies": [],
            "required_skills": ["python"],
            "risk_factors": []
        }
    )
    assert developer.needs_ux_design([ux_task])

@pytest.mark.asyncio
async def test_handle_review_request(
    developer: DeveloperAgent,
    mock_task: Task,
    mock_github_service: Mock
) -> None:
    """Test handling of review requests."""
    # Test data
    review_data = {
        "pr_url": "https://github.com/org/repo/pull/1",
        "files": ["src/test.py"],
        "title": "Test PR",
        "description": "Test PR description",
        "requested_by": "test-reviewer"
    }
    
    # Configure mocks
    mock_github_service.create_review_comment.return_value = True
    
    # Execute
    result = await developer.handle_review_request(review_data)
    
    # Verify
    assert result["status"] == "success"
    assert "comments" in result["data"]
    mock_github_service.create_review_comment.assert_called()

@pytest.mark.asyncio
async def test_create_pr_with_implementations(
    developer: DeveloperAgent,
    mock_tasks: List[Task],
    mock_implementation: Dict[str, Any],
    mock_github_service: Mock
) -> None:
    """Test creation of pull request with implemented tasks."""
    # Create test implementation result
    implementation_result = {
        "implementations": {
            mock_tasks[0].id: {
                "code": mock_implementation["code"],
                "file_path": mock_implementation["file_path"],
                "task": mock_tasks[0].model_dump(),
                "validation": {"valid": True, "errors": []}
            }
        },
        "failed_tasks": []
    }

    # Create PR
    pr_url = await developer.create_pr(implementation_result)

    # Verify PR creation
    assert pr_url == "https://github.com/org/repo/pull/1"
    mock_github_service.create_branch.assert_called_once()
    mock_github_service.commit_changes.assert_called_once()
    mock_github_service.create_pr.assert_called_once()

    # Verify PR content
    call_args = mock_github_service.create_pr.call_args
    assert call_args is not None
    assert mock_tasks[0].title in call_args[1]["body"]
    assert mock_implementation["code"] in call_args[1]["body"]

@pytest.mark.asyncio
async def test_needs_ux_design(
    developer: DeveloperAgent,
    mock_tasks: List[Task]
) -> None:
    """Test UX design requirement detection."""
    # Test with non-UX tasks
    assert not developer.needs_ux_design(mock_tasks)
    
    # Test with UX task
    ux_task = Task(
        id="task-3",
        title="UX Task",
        description="UX task description",
        requires_ux=True,
        metadata={
            "type": "implementation",
            "complexity": 1,
            "dependencies": [],
            "required_skills": ["python"],
            "risk_factors": []
        }
    )
    assert developer.needs_ux_design([ux_task])

@pytest.mark.asyncio
async def test_handle_review_request(
    developer: DeveloperAgent,
    mock_task: Task,
    mock_github_service: Mock
) -> None:
    """Test handling of review requests."""
    # Test data
    review_data = {
        "pr_url": "https://github.com/org/repo/pull/1",
        "files": ["src/test.py"],
        "title": "Test PR",
        "description": "Test PR description",
        "requested_by": "test-reviewer"
    }
    
    # Configure mocks
    mock_github_service.create_review_comment.return_value = True
    
    # Execute
    result = await developer.handle_review_request(review_data)
    
    # Verify
    assert result["status"] == "success"
    assert "comments" in result["data"]
    mock_github_service.create_review_comment.assert_called() 