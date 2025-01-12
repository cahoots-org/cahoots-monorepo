"""Test health check endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.health import router, HealthResponse
from src.utils.config import get_settings
from src.api.dependencies import get_db, get_verified_redis, get_verified_event_system
from src.core.dependencies import BaseDeps

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    return mock

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock()
    mock.verify_connection = AsyncMock()
    return mock

@pytest.fixture
def app(mock_db, mock_event_system, mock_redis):
    """Create test FastAPI app with mocked dependencies."""
    app = FastAPI()
    
    # Override dependencies with mocks
    async def get_mock_db():
        return mock_db
        
    async def get_mock_event_system():
        return mock_event_system
        
    async def get_mock_redis():
        return mock_redis
        
    app.dependency_overrides = {
        get_db: get_mock_db,
        get_verified_event_system: get_mock_event_system,
        get_verified_redis: get_mock_redis,
        BaseDeps: lambda: MagicMock(db=mock_db, event_system=mock_event_system, redis=mock_redis)
    }
    app.include_router(router, prefix="/health")
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    with patch("src.api.dependencies.get_settings") as mock:
        mock.return_value.service_name = "test_service"
        yield mock

def test_health_check_success(client, mock_db, mock_event_system, mock_redis):
    """Test health check succeeds when all services are healthy."""
    # Configure mocks
    mock_event_system.verify_connection.return_value = True
    mock_redis.ping.return_value = True
    
    # Make request
    response = client.get("/health")
    
    # Verify response
    assert response.status_code == 200
    response_data = response.json()
    
    # Check structure and values except latency
    assert response_data["status"] == "healthy"
    assert response_data["database"] == "connected"
    assert response_data["event_system"] == "connected"
    assert response_data["redis"] == "connected"
    assert "services" in response_data
    assert "redis" in response_data["services"]
    assert response_data["services"]["redis"]["status"] == "healthy"
    assert response_data["services"]["redis"]["details"] == {}
    assert isinstance(response_data["services"]["redis"]["latency_ms"], (int, float))
    
    # Verify mocks were called
    mock_db.execute.assert_called_once_with("SELECT 1")
    mock_event_system.verify_connection.assert_called_once()
    mock_redis.ping.assert_called_once()

def test_health_check_db_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when database is unhealthy."""
    mock_db.execute.side_effect = Exception("Database error")
    
    response = client.get("/health")
    
    assert response.status_code == 503
    mock_db.execute.assert_called_once_with("SELECT 1")

def test_health_check_event_system_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when event system is unhealthy."""
    mock_event_system.verify_connection.side_effect = Exception("Event system unavailable")
    
    response = client.get("/health")
    
    assert response.status_code == 503

def test_health_check_redis_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when Redis is unhealthy."""
    # Configure all mocks explicitly
    mock_db.execute.return_value = True  # DB healthy
    mock_event_system.verify_connection.return_value = True  # Event system healthy
    mock_redis.ping.side_effect = Exception("Redis unavailable")  # Redis fails
    
    response = client.get("/health")
    
    assert response.status_code == 503
    
    # Verify all mocks were called
    mock_db.execute.assert_called_once_with("SELECT 1")
    mock_event_system.verify_connection.assert_called_once()
    mock_redis.ping.assert_called_once() 