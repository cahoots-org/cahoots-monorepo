"""Test configuration and fixtures."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
from redis.asyncio import Redis

@pytest.fixture
async def mock_redis():
    """Create a core mock Redis client with essential functionality."""
    mock = AsyncMock(spec=Redis)
    
    # Basic Redis operations
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.publish = AsyncMock(return_value=1)
    
    # PubSub functionality
    pubsub_mock = AsyncMock()
    pubsub_mock.subscribe = AsyncMock()
    pubsub_mock.unsubscribe = AsyncMock()
    pubsub_mock.get_message = AsyncMock(return_value=None)
    mock.pubsub = AsyncMock(return_value=pubsub_mock)
    
    yield mock

@pytest.fixture
async def mock_db():
    """Create a mock database session with core functionality."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    yield mock

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up essential environment variables for tests."""
    # App settings
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_SERVICE_NAME", "ai_dev_team")
    monkeypatch.setenv("APP_HOST", "localhost")
    monkeypatch.setenv("APP_PORT", "8000")
    monkeypatch.setenv("APP_K8S_NAMESPACE", "test-namespace")
    monkeypatch.setenv("APP_MODEL_NAME", "test-model")
    
    # Security settings
    monkeypatch.setenv("SECURITY_JWT_SECRET", "test-jwt-secret-that-is-at-least-32-chars-long")
    monkeypatch.setenv("SECURITY_JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("SECURITY_TOKEN_EXPIRE_MINUTES", "30")
    
    # Database settings
    monkeypatch.setenv("DB_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "10")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "30")
    monkeypatch.setenv("DB_POOL_RECYCLE", "1800")
    monkeypatch.setenv("DB_ECHO", "false")
    
    # Redis settings
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("REDIS_POOL_SIZE", "10")
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "5")
    
    # API settings
    monkeypatch.setenv("API_STRIPE_SECRET", "test-stripe-key")
    monkeypatch.setenv("API_STRIPE_WEBHOOK", "test-webhook-secret")
    monkeypatch.setenv("API_GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("API_TRELLO_KEY", "test-trello-key")
    monkeypatch.setenv("API_TRELLO_SECRET", "test-trello-secret")

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.connect = AsyncMock()
    mock._connected = True
    mock.redis = AsyncMock()
    return mock

@pytest.fixture
def base_app(mock_redis):
    """Create a minimal base FastAPI app for testing."""
    app = FastAPI()
    
    # Add only essential middleware and routers
    from cahoots_core.api.health import router as health_router
    from cahoots_core.api.metrics import router as metrics_router
    
    app.include_router(health_router, prefix="/health")
    app.include_router(metrics_router, prefix="/metrics")
    
    return app

@pytest.fixture
def test_client(base_app):
    """Create a basic test client without dependencies."""
    with TestClient(base_app) as client:
        client.headers = {"X-API-Key": "test_api_key"}
        yield client

@pytest.fixture
async def mock_deps(mock_db, mock_redis):
    """Provide core dependencies for testing."""
    mock = AsyncMock()
    mock.db = mock_db
    mock.redis = mock_redis
    yield mock

@pytest.fixture
async def async_client(base_app):
    """Create an async test client."""
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=base_app), base_url="http://testserver") as client:
        yield client

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create a mock base logger for testing."""
    mock = Mock()
    mock.debug = Mock()
    mock.info = Mock()
    mock.warning = Mock()
    mock.error = Mock()
    return mock