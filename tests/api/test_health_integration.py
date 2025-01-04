"""Tests for health check integration."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_health_check_integration(
    test_client: TestClient,
    mock_event_system: AsyncMock
) -> None:
    """Test the health check endpoint with integrated services."""
    # Configure mock event system
    mock_event_system.is_connected = Mock(return_value=True)
    mock_event_system.connect = AsyncMock()
    mock_event_system.verify_connection = AsyncMock(return_value=True)
    mock_event_system._connected = True
    
    # Configure mock Redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_event_system.get_redis = AsyncMock(return_value=mock_redis)
    mock_event_system.redis_client = mock_redis
    
    # Patch event system
    with patch("src.api.core.get_event_system", return_value=mock_event_system), \
         patch("src.api.core._event_system", mock_event_system):  # Also patch the global instance
        # Ensure event system is connected
        await mock_event_system.connect()
        
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert isinstance(data["uptime_seconds"], int)
        assert data["redis_connected"] is True
        
        # Check Redis service health
        redis_health = data["services"]["redis"]
        assert redis_health["status"] == "healthy"
        assert isinstance(redis_health["latency_ms"], float)
        assert redis_health["details"] == {} 