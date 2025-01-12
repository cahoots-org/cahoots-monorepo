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
async def mock_redis():
    """Create a comprehensive mock Redis client with all needed functionality."""
    mock = AsyncMock(spec=Redis)
    
    # Basic Redis operations
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.publish = AsyncMock(return_value=1)
    mock.hset = AsyncMock(return_value=True)
    mock.hgetall = AsyncMock(return_value={})
    
    # Pipeline functionality
    pipeline_mock = AsyncMock()
    pipeline_mock.execute = AsyncMock()
    mock.pipeline = AsyncMock(return_value=pipeline_mock)
    
    # PubSub functionality
    pubsub_mock = AsyncMock()
    pubsub_mock.ping = AsyncMock(return_value=True)
    pubsub_mock.subscribe = AsyncMock(return_value=True)
    pubsub_mock.unsubscribe = AsyncMock(return_value=True)
    pubsub_mock.get_message = AsyncMock(return_value=None)
    pubsub_mock.close = AsyncMock()
    
    mock.pubsub = AsyncMock(return_value=pubsub_mock)
    return mock

@pytest.fixture
def mock_event_system(mock_redis):
    """Create a mock event system."""
    event_system = AsyncMock(spec=EventSystem)
    event_system.redis = mock_redis
    event_system.is_connected = True
    event_system._connected = True
    event_system.verify_connection = AsyncMock(return_value=True)
    event_system.publish = AsyncMock()
    event_system.subscribe = AsyncMock()
    event_system.unsubscribe = AsyncMock()
    return event_system

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
    monkeypatch.setenv("K8S_NAMESPACE", "test-namespace")

@pytest.fixture
def base_app(mock_redis):
    """Create a base FastAPI app for testing."""
    from fastapi import FastAPI
    from src.api.health import router as health_router
    from src.api.projects import router as projects_router
    from src.api.organizations import router as organizations_router
    from src.api.billing import router as billing_router
    from src.api.webhooks import router as webhooks_router
    from src.api.metrics import router as metrics_router
    from src.api.routers import context
    from src.api.middleware.security import SecurityMiddleware
    from src.utils.security import SecurityManager
    
    app = FastAPI()
    
    # Add security middleware with test security manager
    security_manager = SecurityManager(mock_redis)
    app.add_middleware(SecurityMiddleware, security_manager=security_manager)
    
    # Include routers
    app.include_router(health_router, prefix="/health")
    app.include_router(projects_router, prefix="/api/projects")
    app.include_router(organizations_router, prefix="/api/organizations")
    app.include_router(billing_router, prefix="/api/billing")
    app.include_router(webhooks_router, prefix="/api/webhooks")
    app.include_router(context.router, prefix="/api/context")
    app.include_router(metrics_router, prefix="/metrics")
    
    return app

@pytest.fixture
def test_client(base_app):
    """Create a test client without dependencies.
    
    Note: Use this only for simple route tests that don't need dependencies.
    For routes that need dependencies, create a specific test client in the test file.
    """
    with TestClient(base_app) as client:
        client.headers = {"X-API-Key": "test_api_key"}
        yield client