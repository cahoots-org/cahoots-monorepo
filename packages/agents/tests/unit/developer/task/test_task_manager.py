"""Unit tests for task manager."""
from typing import List
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json

from cahoots_core.ai import AIProvider
from cahoots_core.models.task import Task
from cahoots_core.models.story import Story

from src.cahoots_agents.base import BaseAgent
from src.cahoots_agents.developer.task.task_manager import TaskManager

@pytest.fixture
def ai_provider():
    """Create a mock AI provider."""
    provider = MagicMock()
    provider.generate_response.return_value = json.dumps([{
        "id": "task-1",
        "title": "Test Task",
        "description": "Test task description",
        "requires_ux": False,
        "metadata": {
            "dependencies": [],
            "acceptance_criteria": ["Test criteria"]
        }
    }])
    return provider

@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = AsyncMock()
    agent.generate_response = AsyncMock()
    agent.generate_response.return_value = json.dumps([{
        "id": "task1",
        "title": "Test Task",
        "description": "Test Description",
        "requires_ux": False,
        "metadata": {
            "dependencies": [],
            "acceptance_criteria": []
        }
    }])
    return agent

@pytest.fixture
def task_manager(mock_agent):
    """Create task manager with mocked dependencies."""
    return TaskManager(mock_agent)

@pytest.fixture
def sample_story():
    """Create sample story."""
    return Story(
        id="story123",
        title="Implement feature X",
        description="Add new feature X with the following requirements...",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        metadata={"priority": "high"}
    )

@pytest.mark.asyncio
async def test_break_down_story(task_manager, mock_agent):
    """Test breaking down a story into tasks."""
    story = Story(
        id="test-story",
        title="Test Story",
        description="Test description"
    )
    tasks: List[Task] = await task_manager.break_down_story(story)
    assert len(tasks) == 1
    assert tasks[0].id == "task1"
    assert tasks[0].title == "Test Task"

@pytest.mark.asyncio
async def test_break_down_story_with_requirements(task_manager, mock_agent):
    """Test breaking down a story with requirements."""
    story = Story(
        id="test-story",
        title="Test Story",
        description="Test description"
    )
    requirements = ["Must be fast", "Must be secure"]
    tasks: List[Task] = await task_manager.break_down_story(story, requirements=requirements)
    assert len(tasks) == 1
    assert tasks[0].id == "task1"

@pytest.mark.asyncio
async def test_break_down_story_with_dependencies(task_manager, mock_agent):
    """Test breaking down a story with dependencies."""
    story = Story(
        id="test-story",
        title="Test Story",
        description="Test description"
    )
    dependencies = ["auth", "database"]
    tasks: List[Task] = await task_manager.break_down_story(story, dependencies=dependencies)
    assert len(tasks) == 1
    assert tasks[0].id == "task1"

@pytest.mark.asyncio
async def test_break_down_story_missing_fields(task_manager, mock_agent):
    """Test breaking down a story with missing fields."""
    story = Story(
        id="test-story",
        title="Test Story",
        description=""
    )
    tasks: List[Task] = await task_manager.break_down_story(story)
    assert len(tasks) == 1
    assert tasks[0].id == "task1"

@pytest.mark.asyncio
async def test_break_down_story_with_acceptance_criteria(task_manager, mock_agent):
    """Test story breakdown with detailed acceptance criteria."""
    story = Story(
        id="story123",
        title="User Authentication",
        description="Implement user authentication",
        acceptance_criteria=[
            "Users can sign up with email",
            "Users can login with email/password",
            "Users can reset password",
            "Passwords must be securely hashed"
        ],
        metadata={}
    )
    mock_agent.generate_response.return_value = json.dumps([
        {
            "id": "task1",
            "title": "Implement signup",
            "description": "Create user signup endpoint",
            "metadata": {"acceptance_criteria": ["Users can sign up with email"]}
        },
        {
            "id": "task2",
            "title": "Implement login",
            "description": "Create login endpoint",
            "metadata": {"acceptance_criteria": ["Users can login with email/password"]}
        }
    ])
    tasks = await task_manager.break_down_story(story)
    assert len(tasks) == 2
    assert tasks[0].id == "task1"
    assert tasks[1].id == "task2"
    assert "acceptance_criteria" in tasks[0].metadata
    assert len(tasks[0].metadata["acceptance_criteria"]) > 0

@pytest.mark.asyncio
async def test_break_down_story_empty_response(task_manager, mock_agent):
    """Test breaking down a story with empty response."""
    story = Story(
        id="test-story",
        title="Test Story",
        description="Test description"
    )
    mock_agent.generate_response.return_value = ""
    with pytest.raises(ValueError, match="Failed to parse tasks from AI response"):
        await task_manager.break_down_story(story)

@pytest.mark.asyncio
async def test_break_down_story_success(task_manager, mock_agent):
    """Test successful story breakdown."""
    story = Story(
        id="story123",
        title="User Authentication",
        description="Implement user authentication"
    )
    expected_tasks = [
        {
            "id": "task1",
            "title": "Setup database schema",
            "description": "Create required database tables",
            "metadata": {}
        },
        {
            "id": "task2",
            "title": "Implement API endpoints",
            "description": "Create REST endpoints",
            "metadata": {}
        }
    ]
    mock_agent.generate_response.return_value = json.dumps(expected_tasks)
    tasks = await task_manager.break_down_story(story)
    assert len(tasks) == 2
    assert all(isinstance(task, Task) for task in tasks)

@pytest.mark.asyncio
async def test_break_down_story_invalid_json(task_manager, mock_agent):
    """Test handling of invalid JSON response."""
    story = Story(
        id="story123",
        title="Test Story",
        description="Test description"
    )
    mock_agent.generate_response.return_value = "invalid json"
    with pytest.raises(ValueError, match="Failed to parse tasks"):
        await task_manager.break_down_story(story) 