"""Unit tests for the developer agent."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import os
import json

from cahoots_core.models.task import Task
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus.system import EventSystem
from cahoots_core.ai import AIProvider
from cahoots_core.models.story import Story
from src.cahoots_agents.developer.core.developer import Developer

pytestmark = pytest.mark.asyncio

@pytest.fixture
def ai_provider():
    """Create mock AI provider."""
    provider = MagicMock(spec=AIProvider)
    provider.generate_response = AsyncMock(return_value=json.dumps({
        "status": "success",
        "priority": "medium",
        "changes": [
            {
                "file": "test.py",
                "line": 42,
                "change": "Add error handling"
            }
        ],
        "suggestions": ["Add more tests"]
    }))
    return provider

@pytest.fixture
def event_system():
    """Create a mock event system."""
    system = MagicMock(spec=EventSystem)
    system.publish = AsyncMock()
    system.subscribe = AsyncMock()
    return system

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    event_system = AsyncMock()
    event_system.connect = AsyncMock()
    event_system.publish = AsyncMock()
    return event_system

@pytest.fixture
def github_service():
    """Create mock GitHub service."""
    service = MagicMock(spec=GitHubService)
    service.create_branch = AsyncMock()
    service.commit_changes = AsyncMock()
    service.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    service.get_pr = AsyncMock(return_value={"state": "open"})
    service.update_pr = AsyncMock()
    service.clone_repository = AsyncMock()
    service.create_pull_request = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    return service

@pytest.fixture
def mock_task_manager():
    """Create mock task manager."""
    manager = MagicMock()
    manager.break_down_story = AsyncMock(return_value=[
        Task(id="task1", title="Task 1", description="Description 1", metadata={}),
        Task(id="task2", title="Task 2", description="Description 2", metadata={})
    ])
    return manager

@pytest.fixture
def mock_code_generator():
    """Create mock code generator."""
    generator = MagicMock()
    generator.generate_implementation = AsyncMock(return_value={
        "code": "def test(): pass",
        "file_path": "test.py",
        "validation": {
            "valid": True,
            "errors": []
        }
    })
    return generator

@pytest.fixture
def mock_code_validator():
    """Create mock code validator."""
    validator = MagicMock()
    validator.validate_implementation.return_value = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "metrics": {}
    }
    return validator

@pytest.fixture
def mock_feedback_manager():
    """Create mock feedback manager."""
    manager = Mock()
    manager.process_feedback = AsyncMock(return_value={"status": "success"})
    return manager

@pytest.fixture
def mock_file_manager():
    """Create mock file manager."""
    manager = MagicMock()
    manager.workspace_dir = "/tmp/test_workspace"
    manager.create_file = AsyncMock()
    manager.read_file = AsyncMock(return_value="test content")
    manager.update_file = AsyncMock()
    manager.delete_file = AsyncMock()
    manager.list_files = AsyncMock(return_value=["test.py"])
    manager.determine_file_path = AsyncMock(return_value="test.py")
    manager.gather_implementation_context = AsyncMock(return_value={
        "files": ["test.py"],
        "content": "test content",
        "dependencies": []
    })
    return manager

@pytest.fixture
def mock_pr_manager():
    """Create mock PR manager."""
    manager = Mock()
    manager.handle_review_request = AsyncMock(return_value={"status": "success"})
    return manager

@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = MagicMock()
    agent.config = {
        "provider": "test",
        "api_key": "test-key",
        "models": {
            "default": "test-model",
            "fallback": "test-model-fallback"
        }
    }
    agent.get.return_value = agent.config
    agent.generate_response = AsyncMock(return_value=json.dumps({"status": "success"}))
    agent.stream_response = AsyncMock(return_value=["chunk1", "chunk2"])
    return agent

@pytest.fixture
def mock_github_service():
    """Create mock GitHub service."""
    github_service = AsyncMock()
    github_service.create_branch = AsyncMock()
    github_service.commit_changes = AsyncMock()
    github_service.create_pull_request = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    return github_service

@pytest.fixture
async def developer(mock_event_system, mock_github_service, mock_agent, mock_code_validator, mock_code_generator):
    """Create developer agent for testing."""
    developer = Developer(
        event_system=mock_event_system,
        github_service=mock_github_service,
        ai_provider=mock_agent,
        workspace_dir="test",
        start_listening=True  # Changed to True since we want to test event setup
    )
    developer.logger = MagicMock()
    developer.code_validator = mock_code_validator
    developer.code_generator = mock_code_generator
    await developer.start()  # Explicitly call start to ensure events are set up
    return developer

@pytest.mark.asyncio
async def test_handle_story_assignment(developer, mock_event_system):
    """Test handling a story assignment."""
    developer = await developer
    story = Story(
        id="test-story",
        title="Test Story",
        description="Test description"
    )
    await developer.handle_story_assignment(story)
    mock_event_system.publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_pr_success(developer):
    """Test successful PR creation."""
    developer = await developer
    implementation_result = {
        "implementations": {
            "task1": {
                "code": "def test(): pass",
                "file_path": "test.py",
                "task": {
                    "id": "task1",
                    "title": "Task 1",
                    "description": "Description 1"
                },
                "validation": {"valid": True, "errors": []}
            }
        },
        "failed_tasks": []
    }

    developer.github_service.create_branch = AsyncMock(return_value="test-branch")
    developer.github_service.commit_changes = AsyncMock()
    developer.github_service.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")
    
    pr_url = await developer.create_pr(implementation_result)
    assert pr_url == await developer.github_service.create_pr()

@pytest.mark.asyncio
async def test_create_pull_request(developer):
    """Test creating a pull request."""
    developer = await developer
    task = Task(
        id="test-task",
        title="Test Task",
        description="Test description"
    )

    async def mock_generate_implementation(task):
        return {
            "code": "def test(): pass",
            "file_path": "test.py"
        }

    async def mock_validate_implementation(implementation):
        return {"valid": True, "errors": []}

    developer.code_generator.generate_implementation = mock_generate_implementation
    developer.code_validator.validate_implementation = mock_validate_implementation
    developer.github_service.create_branch = AsyncMock(return_value="test-branch")
    developer.github_service.commit_changes = AsyncMock()
    developer.github_service.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")

    pr_url = await developer.create_pull_request(task)
    assert pr_url == await developer.github_service.create_pr()

@pytest.mark.asyncio
async def test_handle_review_request(developer):
    """Test handling a review request."""
    developer = await developer
    review_data = {
        "pr_number": "123",
        "repo": "test/repo",
        "files_changed": ["test.py"]
    }
    developer.ai.generate_response.return_value = json.dumps({
        "status": "approved",
        "comments": []
    })
    result = await developer.handle_review_request(review_data)
    assert result.get("status") == "approved"

@pytest.mark.asyncio
async def test_handle_review_comments(developer):
    """Test handling review comments."""
    developer = await developer
    result = await developer.handle_review_comments("test-pr", ["test comment"])
    assert result.get("status") == "success"

@pytest.mark.asyncio
async def test_handle_story_assigned_success(developer, mock_event_system):
    """Test successful story assignment handling."""
    developer = await developer
    story_data = {
        "story": {
            "id": "story123",
            "title": "Test Story",
            "description": "Test description",
            "assigned_to": "dev-1",
        "repo_url": "https://github.com/org/repo"
        }
    }

    developer.task_manager = AsyncMock()
    developer.task_manager.break_down_story = AsyncMock(return_value={
        "status": "success",
        "tasks": [
            Task(id="task1", title="Task 1", description="Description 1", metadata={})
        ]
    })
    
    developer.implement_tasks = AsyncMock(return_value={
        "status": "success",
        "implementations": {
            "task1": {
                "code": "def test(): pass",
                "file_path": "test.py",
                "validation": {"valid": True, "errors": []}
            }
        }
    })
    
    developer.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/1")

    result = await developer.handle_story_assigned(story_data)
    assert result.get("status") == "success"
    assert developer.task_manager.break_down_story.await_count == 1
    assert mock_event_system.publish.await_count == 2  # implementation_started and implementation_completed

@pytest.mark.asyncio
async def test_handle_story_assigned_wrong_developer(developer):
    """Test story assignment for wrong developer."""
    developer = await developer
    story_data = {
        "story_id": "story123",
        "assigned_to": "other-dev"
    }
    
    result = await developer.handle_story_assigned({"story": story_data})
    
    assert result.get("status") == "error"
    assert "not assigned to this developer" in result.get("message")

@pytest.mark.asyncio
async def test_implement_tasks_success(developer):
    """Test successful task implementation."""
    developer = await developer
    tasks = [
        Task(id="task1", title="Task 1", description="Description 1", metadata={}),
        Task(id="task2", title="Task 2", description="Description 2", metadata={})
    ]

    async def mock_generate_implementation(task):
        task_num = task.id.replace("task", "")
        return {
            "code": f"def test{task_num}(): pass",
            "file_path": f"test{task_num}.py"
        }

    async def mock_validate_implementation(implementation):
        return {"valid": True, "errors": []}

    developer.code_generator.generate_implementation = mock_generate_implementation
    developer.code_validator.validate_implementation = mock_validate_implementation
    
    result = await developer.implement_tasks(tasks)
    assert len(result.get("implementations")) == 2
    assert result["implementations"]["task1"]["code"] == "def test1(): pass"
    assert result["implementations"]["task2"]["code"] == "def test2(): pass"

@pytest.mark.asyncio
async def test_implement_tasks_with_failure(developer):
    """Test task implementation with failures."""
    developer = await developer
    tasks = [
        Task(id="task1", title="Task 1", description="Description 1", metadata={}),
        Task(id="task2", title="Task 2", description="Description 2", metadata={})
    ]

    async def mock_generate_implementation(task):
        if task.id == "task1":
            return {
                "code": "def test(): pass",
                "file_path": "test.py"
            }
        else:
            raise Exception("Generation failed")

    async def mock_validate_implementation(implementation):
        return {"valid": True, "errors": []}

    developer.code_generator.generate_implementation = mock_generate_implementation
    developer.code_validator.validate_implementation = mock_validate_implementation
    
    result = await developer.implement_tasks(tasks)
    assert len(result.get("implementations")) == 1
    assert len(result.get("failed_tasks")) == 1
    assert result["failed_tasks"][0].task_id == "task2"
    assert result["failed_tasks"][0].error == "Generation failed"

@pytest.mark.asyncio
async def test_create_pr_invalid_implementation(developer):
    """Test PR creation with invalid implementation."""
    developer = await developer
    implementation_result = {
        "implementations": {
            "task1": {
                "validation": {
                    "valid": False,
                    "errors": ["Test error"]
                }
            }
        }
    }
    
    with pytest.raises(ValueError, match="Invalid implementation"):
        await developer.create_pr(implementation_result)

@pytest.mark.asyncio
async def test_handle_feedback(developer):
    """Test feedback handling."""
    developer = await developer
    feedback_data = {
        "task_id": "task-1",
        "feedback": "Test feedback",
        "type": "review"
    }
    result = await developer.handle_feedback(feedback_data)
    assert result.get("status") == "success"

@pytest.mark.asyncio
async def test_needs_ux_design(developer):
    """Test checking if task needs UX design."""
    developer = await developer
    tasks = [
        Task(
            id="test-task",
            title="Test Task",
            description="Test description",
            requires_ux=True
        ),
        Task(
            id="test-task-2",
            title="Test Task 2",
            description="Test description 2",
            requires_ux=False
        )
    ]
    assert developer.needs_ux_design(tasks)  # Should be True since at least one task requires UX
    
    tasks_no_ux = [
        Task(
            id="test-task-3",
            title="Test Task 3",
            description="Test description 3",
            requires_ux=False
        ),
        Task(
            id="test-task-4",
            title="Test Task 4",
            description="Test description 4",
            requires_ux=False
        )
    ]
    assert not developer.needs_ux_design(tasks_no_ux)  # Should be False since no tasks require UX 