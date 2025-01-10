"""Test configuration and fixtures."""
import pytest
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, Mock
from redis.asyncio import Redis

from src.utils.event_system import EventSystem
from src.utils.stripe_client import StripeClient
from src.services.github_service import GitHubService

# Base mock fixtures
@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock(spec=Redis)
    mock.ping.return_value = True
    return mock

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock(spec=EventSystem)
    mock.is_connected = True
    mock.verify_connection.return_value = True
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.disconnect = AsyncMock()
    
    # Add redis mock
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.delete = Mock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock.redis = mock_redis
    
    return mock

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client."""
    mock = MagicMock(spec=StripeClient)
    mock.construct_event = MagicMock()
    mock.handle_webhook_event = AsyncMock()
    return mock

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.fixture
def mock_github_service():
    """Create mock GitHub service."""
    mock = MagicMock(spec=GitHubService)
    mock.create_repository = AsyncMock()
    mock.create_pull_request = AsyncMock()
    mock.commit_changes = AsyncMock()
    mock.merge_pull_request = AsyncMock()
    mock.post_review_comments = AsyncMock()
    return mock

@pytest.fixture
def mock_event_handler():
    """Create mock event handler."""
    mock = MagicMock()
    mock.emit = AsyncMock(return_value={"status": "success"})
    mock.get_processed_events = AsyncMock(return_value=[])
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.register_handler = AsyncMock()
    return mock

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv("DESIGNER_ID", "test-designer-1")
    monkeypatch.setenv("AGENT_TYPE", "test-agent")
    monkeypatch.setenv("TRELLO_API_KEY", "test-key")
    monkeypatch.setenv("TRELLO_API_TOKEN", "test-token")
    monkeypatch.setenv("TRELLO_BOARD_ID", "test-board")

@pytest.fixture
def base_app():
    """Create a base FastAPI app for testing."""
    app = FastAPI()
    return app

@pytest.fixture
def test_client(base_app):
    """Create a test client without dependencies.
    
    Note: Use this only for simple route tests that don't need dependencies.
    For routes that need dependencies, create a specific test client in the test file.
    """
    with TestClient(base_app) as client:
        yield client