"""Tests for the task manager module."""
import pytest
from unittest.mock import Mock, AsyncMock
import json
import logging

from src.agents.developer.task_manager import TaskManager
from src.models.task import Task

@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = Mock()
    agent.generate_response = AsyncMock()
    agent.focus = "backend"
    return agent

@pytest.fixture
def task_manager(mock_agent):
    """Create a task manager instance."""
    return TaskManager(mock_agent)

@pytest.fixture
def sample_story():
    """Create a sample user story."""
    return {
        "title": "User Authentication",
        "description": "Implement user authentication with JWT tokens"
    }

@pytest.fixture
def valid_task_response():
    """Create a valid task breakdown response."""
    return json.dumps({
        "tasks": [
            {
                "title": "Setup Authentication Models",
                "description": "Create user and token models",
                "type": "setup",
                "complexity": 2,
                "dependencies": [],
                "required_skills": ["python", "sqlalchemy"],
                "risk_factors": ["data security"]
            },
            {
                "title": "Implement JWT Logic",
                "description": "Implement JWT token generation and validation",
                "type": "implementation",
                "complexity": 3,
                "dependencies": ["Setup Authentication Models"],
                "required_skills": ["python", "jwt"],
                "risk_factors": ["security", "performance"]
            },
            {
                "title": "Write Authentication Tests",
                "description": "Create comprehensive test suite",
                "type": "testing",
                "complexity": 2,
                "dependencies": ["Implement JWT Logic"],
                "required_skills": ["python", "pytest"],
                "risk_factors": ["test coverage"]
            }
        ]
    })

@pytest.mark.asyncio
async def test_break_down_story_success(task_manager, sample_story, valid_task_response):
    """Test successful story breakdown."""
    task_manager.agent.generate_response.return_value = valid_task_response
    
    tasks = await task_manager.break_down_story(sample_story)
    
    assert len(tasks) == 3
    assert all(isinstance(task, Task) for task in tasks)
    
    # Verify task types
    types = [task.metadata["type"] for task in tasks]
    assert "setup" in types
    assert "implementation" in types
    assert "testing" in types
    
    # Verify task details
    setup_task = next(t for t in tasks if t.metadata["type"] == "setup")
    assert setup_task.title == "Setup Authentication Models"
    assert setup_task.metadata["complexity"] == 2
    assert "python" in setup_task.metadata["required_skills"]
    assert "data security" in setup_task.metadata["risk_factors"]

@pytest.mark.asyncio
async def test_break_down_story_invalid_json(task_manager, sample_story, caplog):
    """Test handling of invalid JSON response."""
    task_manager.agent.generate_response.return_value = "Invalid JSON"
    
    with caplog.at_level(logging.ERROR):
        tasks = await task_manager.break_down_story(sample_story)
    
    assert len(tasks) == 0
    assert "Failed to parse LLM response as JSON" in caplog.text

@pytest.mark.asyncio
async def test_break_down_story_missing_tasks(task_manager, sample_story, caplog):
    """Test handling of response without tasks array."""
    task_manager.agent.generate_response.return_value = json.dumps({"not_tasks": []})
    
    with caplog.at_level(logging.ERROR):
        tasks = await task_manager.break_down_story(sample_story)
    
    assert len(tasks) == 0
    assert "LLM response is not a valid JSON object with tasks array" in caplog.text

@pytest.mark.asyncio
async def test_break_down_story_missing_fields(task_manager, sample_story, caplog):
    """Test handling of tasks with missing required fields."""
    response = json.dumps({
        "tasks": [
            {
                "title": "Incomplete Task",
                # Missing description field
                "type": "setup",
                "complexity": 1
            }
        ]
    })
    task_manager.agent.generate_response.return_value = response
    
    with caplog.at_level(logging.ERROR):
        tasks = await task_manager.break_down_story(sample_story)
    
    assert len(tasks) == 0
    assert "Missing required field" in caplog.text

@pytest.mark.asyncio
async def test_break_down_story_frontend_focus(task_manager, sample_story, valid_task_response):
    """Test story breakdown with frontend focus."""
    task_manager.agent.focus = "frontend"
    task_manager.agent.generate_response.return_value = valid_task_response
    
    tasks = await task_manager.break_down_story(sample_story)
    
    assert all(task.requires_ux for task in tasks)

def test_validate_task_breakdown_success(task_manager):
    """Test successful task breakdown validation."""
    tasks = [
        Task(
            id="1",
            title="Setup Task",
            description="Setup",
            requires_ux=False,
            metadata={
                "type": "setup",
                "complexity": 2,
                "required_skills": ["python"],
                "risk_factors": []
            }
        ),
        Task(
            id="2",
            title="Implementation Task",
            description="Implement",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 3,
                "required_skills": ["python", "jwt"],
                "risk_factors": []
            }
        ),
        Task(
            id="3",
            title="Testing Task",
            description="Test",
            requires_ux=False,
            metadata={
                "type": "testing",
                "complexity": 2,
                "required_skills": ["python", "pytest"],
                "risk_factors": []
            }
        )
    ]
    
    # Should not raise any exceptions
    task_manager._validate_task_breakdown(tasks)

def test_validate_task_breakdown_empty(task_manager):
    """Test validation with empty task list."""
    with pytest.raises(ValueError) as exc_info:
        task_manager._validate_task_breakdown([])
    
    assert "No tasks found" in str(exc_info.value)

def test_validate_task_breakdown_missing_types(task_manager, caplog):
    """Test validation with missing task types."""
    tasks = [
        Task(
            id="1",
            title="Implementation Task",
            description="Implement",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 3,
                "required_skills": ["python"],
                "risk_factors": []
            }
        )
    ]
    
    with caplog.at_level(logging.WARNING):
        task_manager._validate_task_breakdown(tasks)
    
    assert "No setup tasks found" in caplog.text
    assert "No testing tasks found" in caplog.text

def test_validate_task_breakdown_high_complexity(task_manager, caplog):
    """Test validation with high average complexity."""
    tasks = [
        Task(
            id="1",
            title="Complex Task",
            description="Complex",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 5,
                "required_skills": ["python"],
                "risk_factors": []
            }
        ),
        Task(
            id="2",
            title="Another Complex Task",
            description="Complex",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 4,
                "required_skills": ["python"],
                "risk_factors": []
            }
        )
    ]
    
    with caplog.at_level(logging.WARNING):
        task_manager._validate_task_breakdown(tasks)
    
    assert "High average task complexity" in caplog.text

def test_validate_task_breakdown_limited_skills(task_manager, caplog):
    """Test validation with limited skill requirements."""
    tasks = [
        Task(
            id="1",
            title="Simple Task",
            description="Simple",
            requires_ux=False,
            metadata={
                "type": "implementation",
                "complexity": 2,
                "required_skills": ["python"],
                "risk_factors": []
            }
        )
    ]
    
    with caplog.at_level(logging.WARNING):
        task_manager._validate_task_breakdown(tasks)
    
    assert "Limited skill requirements" in caplog.text

@pytest.mark.asyncio
async def test_break_down_story_code_block_response(task_manager, sample_story, valid_task_response):
    """Test handling of response wrapped in code blocks."""
    response = f"```json\n{valid_task_response}\n```"
    task_manager.agent.generate_response.return_value = response
    
    tasks = await task_manager.break_down_story(sample_story)
    
    assert len(tasks) == 3
    assert all(isinstance(task, Task) for task in tasks) 