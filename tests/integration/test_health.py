"""Integration tests for health check endpoint."""
import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from unittest.mock import AsyncMock
from src.utils.event_system import EventSystem
from src.api.core import get_event_system
from src.api.main import app

@pytest.fixture
async def override_event_system(mock_event_system: AsyncMock):
    """Override the event system dependency for testing."""
    async def get_mock_event_system():
        return mock_event_system
    
    app.dependency_overrides[get_event_system] = get_mock_event_system
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_health_check_healthy(
    async_client: AsyncClient,
    mock_event_system: AsyncMock,
    override_event_system: None
):
    """Test health check when all services are healthy."""
    # Configure mock to indicate healthy Redis connection
    mock_event_system.is_connected.return_value = True
    mock_event_system.verify_connection.return_value = True
    mock_event_system.redis = AsyncMock()
    mock_event_system.redis.ping.return_value = True
    mock_event_system._connected = True
    
    # Call health endpoint
    response = await async_client.get("/health")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["redis_connected"] is True
    assert "environment" in data
    assert data["services"]["redis"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(
    async_client: AsyncClient,
    mock_event_system: AsyncMock,
    override_event_system: None
):
    """Test health check when Redis is unhealthy."""
    # Configure mock to indicate unhealthy Redis connection
    mock_event_system.is_connected.return_value = False
    mock_event_system.verify_connection.return_value = False
    mock_event_system.redis = None
    mock_event_system._connected = False
    
    # Call health endpoint
    response = await async_client.get("/health")
    
    # Verify response
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis_connected"] is False
    assert "environment" in data
    assert data["services"]["redis"]["status"] == "unhealthy"

@pytest.mark.asyncio
async def test_health_check_metrics(
    async_client: AsyncClient,
    mock_event_system: AsyncMock,
    override_event_system: None
):
    """Test health check metrics."""
    # Configure mock
    mock_event_system.is_connected.return_value = True
    mock_event_system.verify_connection.return_value = True
    
    # Call health endpoint
    response = await async_client.get("/health")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["redis_connected"] is True
    assert "environment" in data
    assert "metrics" in data
    assert "uptime" in data["metrics"]
    assert "memory_percent" in data["metrics"] 