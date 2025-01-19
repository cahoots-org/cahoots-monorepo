"""Tests for GitHub service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from cahoots_core.services.github_service import GitHubService

@pytest.fixture
def mock_github_service():
    """Create mock GitHub service with specific test functionality."""
    mock = MagicMock(spec=GitHubService)
    mock.create_repository = AsyncMock()
    mock.create_pull_request = AsyncMock()
    mock.commit_changes = AsyncMock()
    mock.merge_pull_request = AsyncMock()
    mock.post_review_comments = AsyncMock()
    return mock 