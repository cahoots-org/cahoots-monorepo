"""Tests for the main API endpoints."""
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, ANY
from fastapi import status, HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.utils.config import ServiceConfig, APIConfig

@pytest.fixture
def api_key_header() -> Dict[str, str]:
    """Create API key header."""
    return {"X-API-Key": "test_api_key"}

@pytest.fixture
def sample_project() -> Dict:
    """Create a sample project for testing."""
    return {
        "id": "test-project-1",
        "name": "Test Project",
        "description": "A test project",
        "stories": [
            {
                "id": "story1",
                "title": "Story 1",
                "description": "First story",
                "priority": 1,
                "status": "open"
            }
        ],
        "github_url": "https://github.com/org/repo"
    }

@pytest.mark.asyncio
async def test_health_check(
    test_client: TestClient,
    mock_event_system: AsyncMock
) -> None:
    """Test the health check endpoint."""
    # Configure mock
    mock_event_system.is_connected = True
    mock_event_system.connect = AsyncMock()
    mock_event_system.verify_connection = AsyncMock(return_value=True)
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_event_system.redis = mock_redis
    mock_event_system._connected = True

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
        assert data["components"]["event_system"] == "healthy"
        
        # Check Redis service health
        redis_health = data["services"]["redis"]
        assert redis_health["status"] == "healthy"
        assert isinstance(redis_health["latency_ms"], float)
        assert redis_health["details"] == {}

@pytest.mark.asyncio
async def test_metrics_endpoint(test_client: TestClient) -> None:
    """Test the metrics endpoint."""
    response = test_client.get("/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "requests_total" in data
    assert "errors_total" in data
    assert "response_time_ms" in data
    assert "active_connections" in data

@pytest.mark.asyncio
async def test_create_project_success(
    test_client: TestClient,
    api_key_header: Dict[str, str]
) -> None:
    """Test successful project creation."""
    project_data = {
        "name": "Test Project",
        "description": "A test project"
    }
    
    with patch("src.api.auth.verify_api_key", return_value=True):
        response = test_client.post("/api/projects", json=project_data, headers=api_key_header)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert "id" in data
        assert "created_at" in data

@pytest.mark.asyncio
async def test_create_project_invalid_data(
    test_client: TestClient,
    api_key_header: Dict[str, str]
) -> None:
    """Test project creation with invalid data."""
    project_data = {
        "name": "",  # Invalid - empty name
        "description": "A test project"
    }
    
    with patch("src.api.auth.verify_api_key", return_value=True):
        response = test_client.post("/api/projects", json=project_data, headers=api_key_header)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

@pytest.mark.asyncio
async def test_create_project_no_auth(test_client: TestClient) -> None:
    """Test project creation without authentication."""
    project_data = {
        "name": "Test Project",
        "description": "A test project"
    }
    
    response = test_client.post("/api/projects", json=project_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_request_tracking(test_client: TestClient) -> None:
    """Test request tracking middleware."""
    response = test_client.get("/health/metrics")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers 