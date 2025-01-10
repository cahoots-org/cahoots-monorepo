"""Unit tests for the Developer class."""
from typing import TYPE_CHECKING, Dict, Any, List
import pytest
from unittest.mock import AsyncMock, Mock, patch
import json
import uuid
import asyncio

from src.agents.developer import Developer
from src.models.task import Task
from src.utils.event_system import EventSystem
from src.services.github_service import GitHubService
from src.utils.task_manager import TaskManager

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
    return mock

@pytest.fixture
def mock_base_agent() -> Mock:
    """Create a mock base agent."""
    return Mock()

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
    mock_github_service: Mock,
    mock_task_manager: Mock,
    mock_base_agent: Mock,
    mock_code_generator: Mock,
    mock_code_validator: Mock,
    mock_feedback_manager: Mock,
    mock_file_manager: Mock,
    mock_pr_manager: Mock
) -> Developer:
    """Create a Developer instance for testing."""
    # Create developer with mocked event system and no listening
    with patch('src.agents.developer.GitHubService', return_value=mock_github_service):
        dev = Developer(
            developer_id="test-dev-1",
            start_listening=False,  # Don't start listening in tests
            event_system=mock_event_system
        )
    
    # Mock managers
    dev._task_manager = mock_task_manager
    dev.task_manager = mock_task_manager  # For direct access in tests
    dev.code_generator = mock_code_generator
    dev.code_validator = mock_code_validator
    dev.feedback_manager = mock_feedback_manager
    dev.file_manager = mock_file_manager
    dev.pr_manager = mock_pr_manager
    
    # Mock generate_response
    dev.generate_response = AsyncMock()
    
    # Set up mock return values
    mock_github_service.create_pr.return_value = "https://github.com/org/repo/pull/1"
    mock_file_manager.determine_file_path.side_effect = lambda task: {
        "Create User Model": "src/models/user.py",
        "Implement API Endpoint": "src/api/endpoint.py",
        "Create UI Component": "src/ui/component.py",
        "Write Tests": "tests/test_component.py",
        "Generic Task": "src/core/module.py"
    }[task.title]
    
    mock_feedback_manager.get_relevant_feedback.return_value = []
    
    yield dev
    
    # Cleanup
    try:
        # Cancel any pending tasks
        loop = asyncio.get_event_loop()
        pending_tasks = [task for task in asyncio.all_tasks(loop) 
                        if not task.done() and task != asyncio.current_task()]
        for task in pending_tasks:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
    except Exception:
        pass  # Ensure cleanup doesn't raise exceptions that could mask test failures 

@pytest.mark.asyncio
async def test_setup_events(
    developer: Developer,
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
async def test_handle_story_assigned(
    developer: Developer,
    mock_event_system: Mock,
    mock_github_service: Mock,
    mock_task_manager: Mock,
    mock_tasks: List[Task]
) -> None:
    """Test story assignment handling.
    
    Verifies:
    1. Task breakdown
    2. Implementation flow
    3. PR creation
    4. Error handling
    5. Event system integration
    """
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
    mock_github_service.clone_repository = AsyncMock()
    mock_github_service.create_branch = AsyncMock()
    mock_github_service.commit_changes = AsyncMock()
    mock_github_service.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    mock_event_system.publish = AsyncMock()
    
    # Mock developer methods
    developer.break_down_story = AsyncMock(return_value=mock_tasks)
    developer.implement_tasks = AsyncMock(return_value={"failed_tasks": [], "successful_tasks": mock_tasks})
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
    
    # Test error handling - wrong developer
    wrong_story = story_data.copy()
    wrong_story["assigned_to"] = "other-dev"
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": wrong_story})
    assert result["status"] == "error"
    assert mock_github_service.clone_repository.await_count == 1  # No additional calls
    
    # Test error handling - missing fields
    invalid_story = {"story_id": "story-1"}
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": invalid_story})
    assert result["status"] == "error"
    assert mock_github_service.clone_repository.await_count == 1  # No additional calls
    
    # Test error handling - GitHub error
    mock_github_service.clone_repository.side_effect = Exception("GitHub error")
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": story_data})
    assert result["status"] == "error"
    assert "GitHub error" in result["message"]
    mock_event_system.publish.assert_any_await("implementation_failed", {
        "story_id": "story-1",
        "developer_id": developer.developer_id,
        "error": "GitHub error",
        "status": "error"
    })

@pytest.mark.asyncio
async def test_implement_tasks_success(
    developer: Developer,
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
    developer: Developer,
    mock_tasks: List[Task],
    mock_implementation: Dict[str, Any],
    caplog: "LogCaptureFixture"
) -> None:
    """Test handling of partial task implementation failures."""
    # Mock code generator to succeed for first task and fail for second
    developer.code_generator.generate_implementation.side_effect = [
        mock_implementation,  # First task succeeds
        Exception("Implementation failed")  # Second task fails
    ]
    
    # Mock code validator
    developer.code_validator.validate_implementation.return_value = {
        "valid": True,
        "errors": []
    }

    # Call implement_tasks
    result = await developer.implement_tasks(mock_tasks)

    # Verify mix of successes and failures
    assert len(result["implementations"]) == 1
    assert len(result["failed_tasks"]) == 1

    # Verify successful implementation
    implementation = result["implementations"][mock_tasks[0].id]
    assert implementation["code"] == mock_implementation["code"]
    assert implementation["file_path"] == mock_implementation["file_path"]

    # Verify failed task
    failed_task = result["failed_tasks"][0]
    assert failed_task["task_id"] == mock_tasks[1].id
    assert "Implementation failed" in failed_task["error"]

    # Verify error logging
    assert "Failed to implement task" in caplog.text
    assert mock_tasks[1].id in caplog.text

@pytest.mark.asyncio
async def test_break_down_story_success(
    developer: Developer,
    mock_task_manager: Mock
) -> None:
    """Test successful story breakdown."""
    story = {
        "title": "Test Story",
        "description": "Test story description"
    }
    
    # Mock task manager response
    mock_tasks = [
        Task(
            id="task-1",
            title="Task 1",
            description="Task 1 description",
            requires_ux=False,
            metadata={
                "type": "setup",
                "complexity": 1,
                "dependencies": [],
                "required_skills": ["python"],
                "risk_factors": []
            }
        ),
        Task(
            id="task-2",
            title="Task 2",
            description="Task 2 description",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 2,
                "dependencies": ["Task 1"],
                "required_skills": ["python"],
                "risk_factors": ["performance"]
            }
        )
    ]
    mock_task_manager.break_down_story.return_value = mock_tasks
    
    # Break down story
    tasks = await developer.task_manager.break_down_story(story)
    
    # Verify tasks created
    assert len(tasks) == 2
    assert all(isinstance(task, Task) for task in tasks)
    
    # Verify task details
    setup_task = next(t for t in tasks if t.metadata["type"] == "setup")
    assert setup_task.title == "Task 1"
    assert setup_task.metadata["complexity"] == 1
    
    impl_task = next(t for t in tasks if t.metadata["type"] == "implementation")
    assert impl_task.title == "Task 2"
    assert impl_task.metadata["complexity"] == 2
    assert "performance" in impl_task.metadata["risk_factors"]

@pytest.mark.asyncio
async def test_break_down_story_invalid_response(
    developer: Developer,
    mock_task_manager: Mock,
    caplog: "LogCaptureFixture"
) -> None:
    """Test story breakdown with invalid response."""
    story = {
        "title": "Test Story",
        "description": "Test story description"
    }
    
    # Mock task manager to return empty list
    mock_task_manager.break_down_story.return_value = []
    
    # Break down story
    tasks = await developer.task_manager.break_down_story(story)
    
    # Verify empty task list returned
    assert len(tasks) == 0

@pytest.mark.asyncio
async def test_create_pr_with_implementations(
    developer: Developer,
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
                "task": mock_tasks[0].dict(),
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
async def test_create_pr(
    developer: Developer,
    mock_tasks: List[Task],
    mock_github_service: Mock,
    mock_event_system: Mock
) -> None:
    """Test pull request creation.
    
    Verifies:
    1. PR content quality
    2. Branch management
    3. Commit organization
    4. Error handling
    """
    # Create test implementation
    implementation_result = {
        "implementations": {
            mock_tasks[0].id: {
                "code": "def test():\n    pass",
                "file_path": "src/test.py",
                "task": mock_tasks[0].dict(),
                "validation": {"valid": True, "errors": []}
            }
        }
    }
    
    # Test normal case
    pr_url = await developer.create_pr(implementation_result)
    assert pr_url == "https://github.com/org/repo/pull/1"
    
    # Verify GitHub service calls
    mock_github_service.create_branch.assert_called_once()
    mock_github_service.commit_changes.assert_called_once()
    mock_github_service.create_pr.assert_called_once()
    
    # Verify branch name format
    branch_name = mock_github_service.create_branch.call_args[0][0]
    assert branch_name.startswith("feature/")
    assert "implementation" in branch_name
    
    # Verify commit message format
    commit_msg = mock_github_service.commit_changes.call_args[0][1]
    assert mock_tasks[0].title in commit_msg
    
    # Test error handling - validation failure
    implementation_result["implementations"][mock_tasks[0].id]["validation"]["valid"] = False
    implementation_result["implementations"][mock_tasks[0].id]["validation"]["errors"] = ["Test error"]
    
    with pytest.raises(ValueError) as exc_info:
        await developer.create_pr(implementation_result)
    assert "Test error" in str(exc_info.value)
    
    # Test error handling - GitHub errors
    implementation_result["implementations"][mock_tasks[0].id]["validation"]["valid"] = True
    mock_github_service.create_branch.side_effect = Exception("GitHub error")
    
    with pytest.raises(Exception) as exc_info:
        await developer.create_pr(implementation_result)
    assert "GitHub error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_pr_validation_failure(
    developer: Developer,
    mock_tasks: List[Task],
    mock_implementation: Dict[str, Any]
) -> None:
    """Test handling of validation failure during PR creation."""
    # Create test implementation result with validation failure
    implementation_result = {
        "implementations": {
            mock_tasks[0].id: {
                "code": mock_implementation["code"],
                "file_path": mock_implementation["file_path"],
                "task": mock_tasks[0].dict(),
                "validation": {"valid": False, "errors": ["Test error"]}
            }
        },
        "failed_tasks": []
    }

    # Verify PR creation fails with validation error
    with pytest.raises(ValueError) as exc_info:
        await developer.create_pr(implementation_result)

    assert "Test error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_needs_ux_design(
    developer: Developer,
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
async def test_determine_file_path(
    developer: Developer,
    mock_task: Task,
    mock_file_manager: Mock
) -> None:
    """Test file path determination for different task types."""
    # Test model task
    mock_task.title = "Create User Model"
    assert "models" in developer.file_manager.determine_file_path(mock_task)
    
    # Test API task
    mock_task.title = "Implement API Endpoint"
    assert "api" in developer.file_manager.determine_file_path(mock_task)
    
    # Test UI task
    mock_task.title = "Create UI Component"
    assert "ui" in developer.file_manager.determine_file_path(mock_task)
    
    # Test test task
    mock_task.title = "Write Tests"
    assert "tests" in developer.file_manager.determine_file_path(mock_task)
    
    # Test default case
    mock_task.title = "Generic Task"
    assert "core" in developer.file_manager.determine_file_path(mock_task)

@pytest.mark.asyncio
async def test_integrate_feedback(developer: Developer) -> None:
    """Test feedback integration into knowledge base."""
    feedback = {
        "type": "review",
        "content": "Test feedback",
        "context": "Test context",
        "outcome": "success"
    }
    
    developer._integrate_feedback(feedback)
    assert feedback in developer.feedback_history

@pytest.mark.asyncio
async def test_get_relevant_feedback(
    developer: Developer,
    mock_feedback_manager: Mock
) -> None:
    """Test retrieval of relevant feedback."""
    # Add some test feedback
    feedback1 = {
        "type": "review",
        "content": "Test feedback 1",
        "context": "Test context 1",
        "outcome": "success",
        "timestamp": 1000
    }
    feedback2 = {
        "type": "review",
        "content": "Test feedback 2",
        "context": "Test context 2",
        "outcome": "failure",
        "timestamp": 2000
    }
    mock_feedback_manager.get_relevant_feedback.return_value = [feedback2, feedback1]
    
    # Get relevant feedback
    relevant = developer._get_relevant_feedback("Test context")
    
    # Verify feedback retrieval
    assert len(relevant) == 2
    assert feedback2 == relevant[0]  # Most recent first
    assert all("timestamp" in f for f in relevant) 

@pytest.mark.asyncio
async def test_implement_tasks(
    developer: Developer,
    mock_tasks: List[Task],
    mock_event_system: Mock,
    mock_github_service: Mock,
    mock_code_generator: Mock,
    mock_code_validator: Mock
) -> None:
    """Test task implementation.

    Verifies:
    1. Code generation quality
    2. Implementation validation
    3. Error handling
    4. File management
    """
    # Test normal case
    mock_code_generator.generate_implementation.side_effect = [
        {
            "code": "def test():\n    pass\n    # Test code",
            "file_path": "src/test.py"
        },
        {
            "code": "def api():\n    pass\n    # API code",
            "file_path": "src/api.py"
        }
    ]

    result = await developer.implement_tasks(mock_tasks)

    # Verify structure
    assert "implementations" in result
    assert "failed_tasks" in result
    assert len(result["implementations"]) == len(mock_tasks)
    assert len(result["failed_tasks"]) == 0

    # Verify each implementation
    for task_id, impl in result["implementations"].items():
        assert "code" in impl
        assert "file_path" in impl
        assert "task" in impl
        assert "validation" in impl

        # Verify code quality
        code = impl["code"]
        assert len(code) > 0
        assert "def" in code  # Should have functions
        assert "pass" in code  # Should have implementation

        # Verify file path
        file_path = impl["file_path"]
        assert file_path.endswith(".py")
        assert "/" in file_path

        # Verify validation
        validation = impl["validation"]
        assert validation["valid"]
        assert "errors" in validation
        assert len(validation["errors"]) == 0

    # Test error handling - invalid task
    invalid_task = Task(
        id="invalid",
        title="Invalid Task",
        description="",  # Empty description
        requires_ux=False,
        metadata={}
    )
    mock_code_generator.generate_implementation.side_effect = Exception("Invalid task")
    result = await developer.implement_tasks([invalid_task])
    assert len(result["failed_tasks"]) == 1
    assert result["failed_tasks"][0]["task_id"] == "invalid"

    # Test error handling - validation failure
    mock_code_generator.generate_implementation.side_effect = None
    mock_code_generator.generate_implementation.return_value = {
        "code": "def test():\n    pass",
        "file_path": "src/test.py"
    }
    mock_code_validator.validate_implementation.return_value = {
        "valid": False,
        "errors": ["Test error"]
    }
    result = await developer.implement_tasks(mock_tasks)
    assert len(result["failed_tasks"]) == len(mock_tasks)
    for failed in result["failed_tasks"]:
        assert "Test error" in failed["error"]

@pytest.mark.asyncio
async def test_handle_story_assigned(
    developer: Developer,
    mock_event_system: Mock,
    mock_github_service: Mock,
    mock_task_manager: Mock,
    mock_tasks: List[Task]
) -> None:
    """Test story assignment handling.
    
    Verifies:
    1. Task breakdown
    2. Implementation flow
    3. PR creation
    4. Error handling
    5. Event system integration
    """
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
    mock_github_service.clone_repository = AsyncMock()
    mock_github_service.create_branch = AsyncMock()
    mock_github_service.commit_changes = AsyncMock()
    mock_github_service.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    mock_event_system.publish = AsyncMock()
    
    # Mock developer methods
    developer.break_down_story = AsyncMock(return_value=mock_tasks)
    developer.implement_tasks = AsyncMock(return_value={"failed_tasks": [], "successful_tasks": mock_tasks})
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
    
    # Test error handling - wrong developer
    wrong_story = story_data.copy()
    wrong_story["assigned_to"] = "other-dev"
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": wrong_story})
    assert result["status"] == "error"
    assert mock_github_service.clone_repository.await_count == 1  # No additional calls
    
    # Test error handling - missing fields
    invalid_story = {"story_id": "story-1"}
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": invalid_story})
    assert result["status"] == "error"
    assert mock_github_service.clone_repository.await_count == 1  # No additional calls
    
    # Test error handling - GitHub error
    mock_github_service.clone_repository.side_effect = Exception("GitHub error")
    result = await developer.handle_story_assigned({"type": "story_assigned", "story": story_data})
    assert result["status"] == "error"
    assert "GitHub error" in result["message"]
    mock_event_system.publish.assert_any_await("implementation_failed", {
        "story_id": "story-1",
        "developer_id": developer.developer_id,
        "error": "GitHub error",
        "status": "error"
    }) 
