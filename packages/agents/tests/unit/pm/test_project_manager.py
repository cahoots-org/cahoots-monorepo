"""Unit tests for project manager."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json

from ....src.cahoots_agents.pm.project_manager import ProjectManager
from cahoots_core.models.story import Story
from cahoots_core.models.task import Task

@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = MagicMock()
    agent.provider = "test"  # This is the key property that AIProviderFactory checks
    agent.generate_response = AsyncMock()
    agent.stream_response = AsyncMock(return_value=["chunk1", "chunk2"])
    return agent

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    return MagicMock()

@pytest.fixture
def project_manager(mock_agent, mock_event_system):
    """Create project manager with mocked dependencies."""
    return ProjectManager(
        ai_provider=mock_agent,
        event_system=mock_event_system,
        config={
            "ai": {
                "provider": "test",
                "api_key": "test-key",
                "models": {
                    "default": "test-model",
                    "fallback": "test-model-fallback"
                }
            }
        }
    )

@pytest.fixture
def sample_story():
    """Create sample story data."""
    return Story(
        id="story123",
        title="Implement User Authentication",
        description="Add JWT-based user authentication",
        acceptance_criteria=[
            "Users can sign up",
            "Users can log in",
            "Passwords are securely hashed"
        ],
        metadata={
            "priority": "high",
            "complexity": "medium"
        }
    )

@pytest.mark.asyncio
async def test_create_story_success(project_manager, sample_story):
    """Test successful story creation."""
    expected_response = {
        "status": "success",
        "story": sample_story.model_dump(),
        "tasks": [
            {
                "id": "task1",
                "title": "Setup Database Schema",
                "description": "Create user table"
            }
        ]
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.create_story(sample_story)
    
    assert result == expected_response

@pytest.mark.asyncio
async def test_create_story_invalid_json(project_manager, sample_story):
    """Test handling of invalid JSON response."""
    project_manager.agent.generate_response.return_value = "invalid json"
    
    with pytest.raises(ValueError, match="Failed to parse story creation response"):
        await project_manager.create_story(sample_story)

@pytest.mark.asyncio
async def test_assign_story_success(project_manager):
    """Test successful story assignment."""
    story_id = "story123"
    developer_id = "dev456"
    expected_response = {
        "status": "success",
        "story_id": story_id,
        "assigned_to": developer_id
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.assign_story(story_id, developer_id)
    
    assert result == expected_response
    project_manager.event_system.publish.assert_called_once()

@pytest.mark.asyncio
async def test_review_story_completion_success(project_manager, sample_story):
    """Test successful story completion review."""
    completion_data = {
        "story": sample_story.model_dump(),
        "tasks": [
            {
                "id": "task1",
                "title": "Setup Database Schema",
                "status": "completed",
                "implementation": {
                    "files": ["user.py"],
                    "changes": ["+100 -20"]
                }
            }
        ]
    }
    expected_response = {
        "status": "approved",
        "feedback": "All acceptance criteria met"
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.review_story_completion(completion_data)
    
    assert result == expected_response

@pytest.mark.asyncio
async def test_review_story_completion_needs_changes(project_manager, sample_story):
    """Test story completion review requiring changes."""
    completion_data = {
        "story": sample_story.model_dump(),
        "tasks": [
            {
                "id": "task1",
                "title": "Setup Database Schema",
                "status": "completed",
                "implementation": {
                    "files": ["user.py"],
                    "changes": ["+50 -10"]
                }
            }
        ]
    }
    expected_response = {
        "status": "changes_needed",
        "feedback": "Missing password hashing implementation",
        "required_changes": [
            {
                "task_id": "task1",
                "description": "Add password hashing"
            }
        ]
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.review_story_completion(completion_data)
    
    assert result.get("status") == "changes_needed"
    assert len(result.get("required_changes")) > 0

@pytest.mark.asyncio
async def test_handle_story_feedback(project_manager):
    """Test handling story feedback."""
    feedback_data = {
        "story_id": "story123",
        "feedback": "Need better error handling",
        "type": "technical",
        "from": "reviewer1"
    }
    expected_response = {
        "status": "success",
        "actions": [
            {
                "type": "create_task",
                "task": {
                    "title": "Improve error handling",
                    "description": "Add comprehensive error handling"
                }
            }
        ]
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.handle_story_feedback(feedback_data)
    
    assert result == expected_response
    project_manager.event_system.publish.assert_called()

@pytest.mark.asyncio
async def test_prioritize_stories(project_manager):
    """Test story prioritization."""
    stories = [
        Story(
            id="story1",
            title="Feature A",
            description="Important feature",
            metadata={"priority": "medium"}
        ),
        Story(
            id="story2",
            title="Bug fix",
            description="Critical bug",
            metadata={"priority": "high"}
        )
    ]
    expected_response = {
        "status": "success",
        "prioritized_stories": [
            {"id": "story2", "priority": 1},
            {"id": "story1", "priority": 2}
        ]
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    Any
    result: Dict[str, Any] = await project_manager.prioritize_stories(stories)
    
    assert result == expected_response
    assert result.get("prioritized_stories")[0].get("id") == "story2"  # High priority first

@pytest.mark.asyncio
async def test_estimate_story_complexity(project_manager, sample_story):
    """Test story complexity estimation."""
    expected_response = {
        "status": "success",
        "complexity": "high",
        "estimated_hours": 20,
        "factors": [
            "Multiple integrations required",
            "Security considerations",
            "Database schema changes"
        ]
    }
    project_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await project_manager.estimate_story_complexity(sample_story)
    
    assert result == expected_response