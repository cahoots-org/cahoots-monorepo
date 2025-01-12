"""Tests for agent factory."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agents.factory import AgentFactory
from src.services.github_service import GitHubService
from src.utils.config import GitHubConfig
from src.utils.event_system import EventSystem

@pytest.fixture
def mock_github_service():
    """Create a mock GitHub service."""
    config = GitHubConfig(
        name="github",
        url="https://api.github.com",
        api_key="test-key",
        workspace_dir="/tmp/workspace",
        repo_name="test-repo"
    )
    return GitHubService(config)

@pytest.fixture
def agent_factory(mock_redis, mock_github_service):
    """Create an agent factory with mocked dependencies."""
    event_system = EventSystem(mock_redis)
    return AgentFactory(
        event_system=event_system,
        github_service=mock_github_service
    )

async def test_agent_creation_and_behavior(agent_factory):
    """Create each type of agent and verify they have required dependencies."""
    # Create each type of agent
    for agent_type in ["project_manager", "developer", "ux_designer", "qa_tester"]:
        agent = agent_factory.create_agent(agent_type)
        assert agent is not None
        # Only these agents require github_service
        if agent_type in ["project_manager", "developer", "ux_designer"]:
            assert agent.github_service is not None

async def test_agent_error_handling(agent_factory, monkeypatch):
    """Test error handling for invalid agent types."""
    # Test invalid agent type
    with pytest.raises(RuntimeError, match="Failed to create agent: Invalid agent type"):
        agent_factory.create_agent("invalid_type")

    # Test missing environment variable
    monkeypatch.delenv("AGENT_TYPE", raising=False)
    with pytest.raises(RuntimeError, match="Failed to create agent: AGENT_TYPE environment variable must be set"):
        agent_factory.create_agent(None) 