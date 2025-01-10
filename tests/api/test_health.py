"""Test health check endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.health import router, HealthResponse
from src.utils.config import config

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
    mock.is_connected = True
    mock.verify_connection = AsyncMock()
    return mock

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock()
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
        "get_session": get_mock_db,
        "get_verified_event_system": get_mock_event_system,
        "get_verified_redis": get_mock_redis
    }
    app.include_router(router)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_config():
    """Mock config for all tests."""
    with patch("src.api.dependencies.config") as mock:
        mock.service_name = "test_service"
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
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
        "event_system": "connected",
        "redis": "connected"
    }
    
    # Verify mocks were called
    mock_db.execute.assert_called_once_with("SELECT 1")
    mock_event_system.verify_connection.assert_called_once()
    mock_redis.ping.assert_called_once()

def test_health_check_db_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when database is unhealthy."""
    mock_db.execute.side_effect = Exception("Database error")
    
    response = client.get("/health")
    
    assert response.status_code == 503
    assert response.json() == {"detail": "Database error"}
    mock_db.execute.assert_called_once_with("SELECT 1")

def test_health_check_event_system_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when event system is unhealthy."""
    mock_event_system.verify_connection.return_value = False
    
    response = client.get("/health")
    
    assert response.status_code == 503
    assert response.json() == {"detail": "Event system unavailable"}
    mock_db.execute.assert_called_once_with("SELECT 1")
    mock_event_system.verify_connection.assert_called_once()

def test_health_check_redis_failure(client, mock_db, mock_event_system, mock_redis):
    """Test health check fails when Redis is unhealthy."""
    mock_event_system.verify_connection.return_value = True
    mock_redis.ping.return_value = False
    
    response = client.get("/health")
    
    assert response.status_code == 503
    assert response.json() == {"detail": "Redis unavailable"}
    mock_db.execute.assert_called_once_with("SELECT 1")
    mock_event_system.verify_connection.assert_called_once()
    mock_redis.ping.assert_called_once() 