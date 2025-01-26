"""Unit tests for PR manager."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from cahoots_core.services.github_service import GitHubService
from cahoots_core.models.task import Task

from .....src.cahoots_agents.base import BaseAgent
from .....src.cahoots_agents.developer.pr.pr_manager import PRManager, PRStatus, PRReviewStatus

@pytest.fixture
def agent():
    """Create a mock agent."""
    agent = MagicMock(spec=BaseAgent)
    agent.generate_response = AsyncMock(return_value=json.dumps({
        "title": "Test PR",
        "body": "Test description",
        "labels": ["test"]
    }))
    return agent

@pytest.fixture
def github_service():
    """Create a mock GitHub service."""
    service = MagicMock(spec=GitHubService)
    service.create_branch = AsyncMock()
    service.commit_changes = AsyncMock()
    service.create_pull_request = AsyncMock()
    service.get_pull_request = AsyncMock()
    service.update_pull_request = AsyncMock()
    service.get_pr = AsyncMock(return_value={"state": "open"})
    service.update_pr = AsyncMock()
    service.get_pr_comments = AsyncMock(return_value=["Test comment"])
    return service

@pytest.fixture
def pr_manager(agent, github_service):
    """Create a test PR manager."""
    return PRManager(agent=agent, github_service=github_service)

@pytest.fixture
def sample_pr_data():
    """Create sample PR data."""
    return {
        "title": "Feature: User Authentication",
        "description": "Implements user authentication using JWT",
        "branch": "feature/auth",
        "base": "main",
        "tasks": [
            Task(
                id="task1",
                title="Implement JWT auth",
                description="Add JWT authentication",
                metadata={"status": "completed"}
            )
        ]
    }

@pytest.mark.asyncio
async def test_generate_pr_description(pr_manager, sample_pr_data):
    """Test successful PR description generation."""
    expected_description = {
        "title": "Feature: User Authentication",
        "body": "## Changes\n- Implements JWT authentication\n\n## Tasks\n- [x] Implement JWT auth",
        "labels": ["feature", "auth"]
    }
    pr_manager.agent.generate_response.return_value = json.dumps(expected_description)
    
    description = await pr_manager.generate_pr_description(sample_pr_data)
    
    assert description == expected_description

@pytest.mark.asyncio
async def test_handle_review_request(pr_manager):
    """Test handling a review request."""
    review_data = {
        "pr_number": "123",
        "repo": "test/repo",
        "files_changed": ["test.py"]
    }
    expected_review = {
        "status": "approved",
        "comments": [
            {
                "file": "test.py",
                "line": 42,
                "comment": "Consider adding error handling",
                "suggestion": "try:\n    do_something()\nexcept Exception as e:\n    handle_error(e)"
            }
        ]
    }
    pr_manager.agent.generate_response.return_value = json.dumps(expected_review)
    
    feedback = await pr_manager.handle_review_request(review_data)
    assert feedback == expected_review

@pytest.mark.asyncio
async def test_handle_review_comments(pr_manager):
    """Test handling review comments."""
    expected_changes = {
        "status": "success",
        "changes": [
            {
                "file": "test.py",
                "line": 42,
                "change": "Add error handling"
            }
        ]
    }
    pr_manager.agent.generate_response.return_value = json.dumps(expected_changes)
    
    suggestions = await pr_manager.handle_review_comments("test-pr", ["Add error handling"])
    assert suggestions == expected_changes

@pytest.mark.asyncio
async def test_get_pr_status(pr_manager, github_service):
    """Test getting PR status."""
    pr_data = {"state": "open"}
    github_service.get_pr.return_value = pr_data
    
    status = await pr_manager.get_pr_status("test-pr")
    assert status == PRStatus.OPEN
    github_service.get_pr.assert_called_once_with("test-pr")

@pytest.mark.asyncio
async def test_update_pr_description(pr_manager, github_service):
    """Test updating PR description."""
    await pr_manager.update_pr_description("test-pr", "New description")
    github_service.update_pull_request.assert_called_once_with(
        "test-pr",
        {"body": "New description"}
    )

@pytest.mark.asyncio
async def test_handle_review_request_invalid_json(pr_manager):
    """Test handling of invalid JSON in review response."""
    review_data = {
        "pr_number": "123",
        "repo": "test/repo",
        "files_changed": []
    }
    pr_manager.agent.generate_response.return_value = "invalid json"
    
    with pytest.raises(ValueError, match="Failed to parse review response"):
        await pr_manager.handle_review_request(review_data)

@pytest.mark.asyncio
async def test_handle_review_request_invalid_status(pr_manager):
    """Test handling of invalid review status."""
    review_data = {
        "pr_number": "123",
        "repo": "test/repo",
        "files_changed": []
    }
    pr_manager.agent.generate_response.return_value = json.dumps({
        "status": "invalid_status",
        "comments": []
    })
    
    with pytest.raises(ValueError, match="Invalid review status"):
        await pr_manager.handle_review_request(review_data)

@pytest.mark.asyncio
async def test_handle_review_request_with_suggestions(pr_manager):
    """Test review request handling with code suggestions."""
    review_data = {
        "pr_number": "123",
        "repo": "test/repo",
        "files_changed": [
            {"name": "auth.py", "changes": "+30 -10"}
        ]
    }
    expected_review = {
        "status": "changes_requested",
        "comments": [
            {
                "file": "auth.py",
                "line": 42,
                "comment": "Consider this improvement",
                "suggestion": "def improved_auth(): pass"
            }
        ]
    }
    pr_manager.agent.generate_response.return_value = json.dumps(expected_review)
    
    result = await pr_manager.handle_review_request(review_data)
    assert result == expected_review