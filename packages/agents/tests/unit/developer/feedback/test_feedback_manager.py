"""Unit tests for feedback manager."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock
import json

from cahoots_core.models.task import Task
from .....src.cahoots_agents.developer.feedback.feedback_manager import FeedbackManager

@pytest.fixture
def mock_agent():
    """Create mock developer agent."""
    agent = Mock()
    agent.generate_response = AsyncMock()
    return agent

@pytest.fixture
def feedback_manager(mock_agent):
    """Create feedback manager with mocked agent."""
    return FeedbackManager(mock_agent)

@pytest.fixture
def sample_feedback():
    """Create sample feedback data."""
    return {
        "task_id": "task123",
        "feedback": "The implementation needs better error handling",
        "type": "code_review",
        "metadata": {
            "file": "auth.py",
            "line": 42
        }
    }

@pytest.mark.asyncio
async def test_process_feedback_success(feedback_manager, sample_feedback):
    """Test successful feedback processing."""
    expected_response = {
        "status": "success",
        "priority": "medium",
        "changes": [
            {
                "file": "auth.py",
                "line": 42,
                "change": "Add try-catch block"
            }
        ]
    }
    feedback_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await feedback_manager.process_feedback(sample_feedback)
    
    assert result == expected_response

@pytest.mark.asyncio
async def test_process_feedback_invalid_json(feedback_manager, sample_feedback):
    """Test handling of invalid JSON response."""
    feedback_manager.agent.generate_response.return_value = "invalid json"
    
    with pytest.raises(ValueError, match="Failed to parse feedback response"):
        await feedback_manager.process_feedback(sample_feedback)

@pytest.mark.asyncio
async def test_process_feedback_missing_fields(feedback_manager):
    """Test handling of feedback with missing required fields."""
    invalid_feedback = {
        "feedback": "Test feedback"
        # Missing task_id and type
    }
    
    with pytest.raises(ValueError, match="Invalid feedback format"):
        await feedback_manager.process_feedback(invalid_feedback)

@pytest.mark.asyncio
async def test_process_feedback_with_suggestions(feedback_manager):
    """Test feedback processing with code suggestions."""
    feedback_with_suggestions = {
        "task_id": "task123",
        "feedback": "Consider using a decorator for authentication",
        "type": "suggestion",
        "metadata": {
            "file": "auth.py",
            "suggestions": [
                {
                    "code": "@require_auth\ndef protected_route():",
                    "description": "Add authentication decorator"
                }
            ]
        }
    }
    expected_response = {
        "status": "success",
        "changes": [
            {
                "file": "auth.py",
                "type": "suggestion",
                "suggestion": "@require_auth\ndef protected_route():",
                "description": "Add authentication decorator"
            }
        ]
    }
    feedback_manager.agent.generate_response.return_value = json.dumps(expected_response)
    Any
    result: Dict[str, Any] = await feedback_manager.process_feedback(feedback_with_suggestions)
    
    assert result.get("status") == "success"
    assert len(result.get("changes")) == 1
    assert "suggestion" in result.get("changes")[0]

@pytest.mark.asyncio
async def test_process_feedback_with_multiple_files(feedback_manager):
    """Test feedback processing affecting multiple files."""
    multi_file_feedback = {
        "task_id": "task123",
        "feedback": "Move authentication logic to separate module",
        "type": "refactor",
        "metadata": {
            "files": ["auth.py", "views.py"]
        }
    }
    expected_response = {
        "status": "success",
        "changes": [
            {
                "file": "auth.py",
                "change": "Extract authentication class"
            },
            {
                "file": "views.py",
                "change": "Update imports and usage"
            }
        ]
    }
    feedback_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await feedback_manager.process_feedback(multi_file_feedback)
    
    assert result.get("status") == "success"
    assert len(result.get("changes")) == 2
    assert all(change.get("file") in ["auth.py", "views.py"] for change in result.get("changes"))

@pytest.mark.asyncio
async def test_process_feedback_with_task_context(feedback_manager):
    """Test feedback processing with task context."""
    task = Task(
        id="task123",
        title="Implement authentication",
        description="Add JWT authentication",
        metadata={
            "requirements": {
                "auth_type": "jwt"
            }
        }
    )
    feedback = {
        "task_id": task.id,
        "feedback": "Use refresh tokens for better security",
        "type": "security",
        "metadata": {
            "file": "auth.py",
            "task": task.model_dump()
        }
    }
    expected_response = {
        "status": "success",
        "changes": [
            {
                "file": "auth.py",
                "change": "Add refresh token handling"
            }
        ]
    }
    feedback_manager.agent.generate_response.return_value = json.dumps(expected_response)
    
    result = await feedback_manager.process_feedback(feedback)
    
    assert result.get("status") == "success"