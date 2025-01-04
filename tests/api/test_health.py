"""Tests for health check endpoint."""
import pytest
from unittest.mock import AsyncMock, Mock
from src.api.health import health_check
from src.utils.event_system import EventSystem

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock(spec=EventSystem)
    return mock

@pytest.mark.asyncio
async def test_health_check_healthy(mock_event_system):
    """Test health check when all systems are healthy."""
    mock_event_system.is_connected.return_value = True
    
    response = await health_check(mock_event_system)
    
    assert response["status"] == "healthy"
    assert response["components"]["event_system"] == "healthy"
    assert "timestamp" in response

@pytest.mark.asyncio
async def test_health_check_event_system_unhealthy(mock_event_system):
    """Test health check when event system is unhealthy."""
    mock_event_system.is_connected.return_value = False
    
    response = await health_check(mock_event_system)
    
    assert response["status"] == "unhealthy"
    assert response["components"]["event_system"] == "unhealthy"
    assert "timestamp" in response

@pytest.mark.asyncio
async def test_health_check_error(mock_event_system):
    """Test health check when there's an error checking component health."""
    mock_event_system.is_connected.side_effect = Exception("Connection error")
    
    response = await health_check(mock_event_system)
    
    assert response["status"] == "unhealthy"
    assert response["components"]["event_system"] == "error"
    assert "timestamp" in response 