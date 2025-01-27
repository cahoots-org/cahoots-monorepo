"""Tests for GitHub service."""
import pytest
from unittest.mock import Mock, AsyncMock
from cahoots_core.services.github_service import GitHubService
from cahoots_core.utils.config import Config
import subprocess

@pytest.fixture
def github_service():
    """Create GitHub service fixture."""
    config = Config(
        api_key="test-token",
        workspace_dir="/tmp/test",
        repo_name="test-repo",
        name="test-service",
        url="https://api.github.com"
    )
    
    github_client = Mock()
    repo = Mock()
    base_branch = Mock()
    
    # Setup mock responses
    repo.get_branch.return_value = base_branch
    github_client.get_repo.return_value = repo
    
    return GitHubService(config=config, github_client=github_client)

@pytest.mark.asyncio
async def test_create_branch(github_service):
    """Test creating a branch."""
    # Setup mocks
    repo = Mock()
    base_branch = Mock()
    base_branch.commit.sha = "test-sha"
    repo.get_branch.return_value = base_branch
    ref = Mock()
    ref.ref = "refs/heads/test-branch"
    repo.create_git_ref.return_value = ref
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    result = github_service.create_branch("test-repo", "test-branch")
    assert result == "refs/heads/test-branch"

@pytest.mark.asyncio
async def test_commit_changes(github_service):
    """Test committing changes."""
    # Setup mocks
    repo = Mock()
    file = Mock()
    file.sha = "test-sha"
    repo.get_contents.return_value = file
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"
    github_service.create_pull_request = Mock(return_value="http://test/pr/1")

    # Test
    result = github_service.commit_changes(
        "test-repo",
        "test-branch",
        {"test.py": "test content"},
        "test commit"
    )
    assert result == "http://test/pr/1"

@pytest.mark.asyncio
async def test_get_file_content(github_service):
    """Test getting file content."""
    # Setup mocks
    repo = Mock()
    file = Mock()
    file.content = "dGVzdCBjb250ZW50"  # base64 for "test content"
    repo.get_contents.return_value = file
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    result = await github_service.get_file_content("test.py", "main")
    assert result == "test content"

@pytest.mark.asyncio
async def test_run_git_command_error(github_service):
    """Test handling git command errors."""
    with pytest.raises(Exception):
        await github_service.run_git_command("invalid command")

@pytest.mark.asyncio
async def test_create_pr(github_service):
    """Test creating a pull request."""
    # Setup mocks
    repo = Mock()
    pr = Mock()
    pr.html_url = "http://test/pr/1"
    repo.create_pull.return_value = pr
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    result = github_service.create_pull_request(
        "test-repo",
        "test-branch",
        "test title",
        "test body"
    )
    assert result == "http://test/pr/1"

@pytest.mark.asyncio
async def test_add_pr_comment(github_service):
    """Test adding a PR comment."""
    # Setup mocks
    repo = Mock()
    pr = Mock()
    pr.create_review = AsyncMock()
    repo.get_pull.return_value = pr
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    await github_service.post_review_comments(
        1,
        [{"body": "test comment"}],
        True,
        "LGTM"
    )
    pr.create_review.assert_called_once()

@pytest.mark.asyncio
async def test_update_pr_status(github_service):
    """Test updating PR status."""
    # Setup mocks
    repo = Mock()
    pr = Mock()
    pr.edit = Mock()
    repo.get_pull.return_value = pr
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    await github_service.update_pr_status(1, "closed")
    pr.edit.assert_called_once_with(state="closed")

@pytest.mark.asyncio
async def test_clone_repository(github_service, monkeypatch):
    """Test cloning a repository."""
    def mock_run(*args, **kwargs):
        class MockCompletedProcess:
            returncode = 0
        return MockCompletedProcess()
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    result = github_service.clone_repository("http://test/repo.git")
    assert result == "/tmp/test/repo"

@pytest.mark.asyncio
async def test_get_pr_files(github_service):
    """Test getting PR files."""
    # Setup mocks
    repo = Mock()
    pr = Mock()
    file = Mock()
    file.filename = "test.py"
    pr.get_files.return_value = [file]
    repo.get_pull.return_value = pr
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    result = await github_service.get_pull_request(1)
    assert "test.py" in result["changed_files"]

@pytest.mark.asyncio
async def test_get_repository_info(github_service):
    """Test getting repository info."""
    # Setup mocks
    repo = Mock()
    repo.clone_url = "http://test/repo.git"
    repo.default_branch = "main"
    github_service.github.get_repo.return_value = repo
    github_service.github.get_user().login = "test-user"

    # Test
    result = await github_service.get_repository_info("test-repo")
    assert result["clone_url"] == "http://test/repo.git"
    assert result["default_branch"] == "main" 