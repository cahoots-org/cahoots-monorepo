"""Integration tests for health check endpoint."""
import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from unittest.mock import AsyncMock

from src.utils.event_system import EventSystem


@pytest.mark.asyncio
async def test_health_check_healthy(
    async_client: AsyncClient,
    mock_event_system: AsyncMock
):
    """Test health check when all services are healthy."""
    # Ensure Redis is connected
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


@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(
    async_client: AsyncClient,
    redis_client: "Redis",
    event_system: "EventSystem"
):
    """Test health check when Redis is unhealthy."""
    # Disconnect Redis
    try:
        await event_system.disconnect()
    except Exception:
        # Ignore any errors during disconnect
        pass

    # Call health endpoint
    response = await async_client.get("/health")

    # Verify response
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis_connected"] is False


@pytest.mark.asyncio
async def test_health_check_metrics(
    async_client: AsyncClient,
    mock_event_system: AsyncMock
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
    assert "memory_usage" in data["metrics"] 