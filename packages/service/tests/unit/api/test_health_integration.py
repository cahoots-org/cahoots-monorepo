"""Integration tests for health check endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from src.api.main import app
from src.core.dependencies import BaseDeps

@pytest.mark.asyncio
async def test_health_check_integration(mock_redis) -> None:
    """Test health check endpoint with integrated dependencies."""
    # Create mock DB
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=1)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Create mock event system
    mock_event_system = AsyncMock()
    mock_event_system.verify_connection = AsyncMock(return_value=True)
    
    # Create deps with mocked services
    deps = BaseDeps()
    deps.db = mock_db
    deps.event_system = mock_event_system
    deps.redis = mock_redis
    
    # Override the app's dependency
    app.dependency_overrides[BaseDeps] = lambda: deps
    
    # Use test client
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["event_system"] == "connected"
        assert data["redis"] == "connected"
        
        # Check Redis service health
        redis_health = data["services"]["redis"]
        assert redis_health["status"] == "healthy"
        assert isinstance(redis_health["latency_ms"], float)
        assert redis_health["details"] == {}
        
    # Clean up
    app.dependency_overrides.clear() 