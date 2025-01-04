"""Tests for the main API endpoints."""
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, ANY
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.utils.config import ServiceConfig, APIConfig

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
    mock_event_system.is_connected = Mock(return_value=True)
    mock_event_system.connect = AsyncMock()
    mock_event_system.verify_connection = AsyncMock(return_value=True)
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_event_system.get_redis = AsyncMock(return_value=mock_redis)
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
        
        # Check Redis service health
        redis_health = data["services"]["redis"]
        assert redis_health["status"] == "healthy"
        assert isinstance(redis_health["latency_ms"], float)
        assert redis_health["details"] == {}

@pytest.mark.asyncio
async def test_create_project_success(
    test_client: TestClient,
    sample_project: Dict,
    api_key_header: Dict,
    mock_event_system: AsyncMock
) -> None:
    """Test successful project creation."""
    # Configure mock
    mock_event_system.is_connected = Mock(return_value=True)
    mock_event_system.connect = AsyncMock()
    mock_event_system.publish = AsyncMock()
    mock_event_system.get_redis = AsyncMock()
    mock_event_system._connected = True
    mock_event_system.redis_client = Mock()
    
    # Patch get_event_system to return our mock
    with patch("src.api.core.get_event_system", return_value=mock_event_system), \
         patch("src.api.core._event_system", mock_event_system):  # Also patch the global instance
        # Ensure event system is connected
        await mock_event_system.connect()
        
        # Create a project without the deadline field
        project_data = {
            "id": sample_project["id"],
            "name": sample_project["name"],
            "description": sample_project["description"],
            "stories": sample_project.get("stories", []),
            "github_url": sample_project.get("github_url")
        }
        
        response = test_client.post(
            "/projects",
            json=project_data,
            headers=api_key_header
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["project_id"] == project_data["id"]
        
        # Verify event was published
        mock_event_system.publish.assert_called_once_with(
            "project_created",
            {
                "project_id": project_data["id"],
                "timestamp": ANY,
                "type": "project_created",
                "payload": project_data
            }
        )

@pytest.mark.asyncio
async def test_create_project_invalid_data(
    test_client: TestClient,
    api_key_header: Dict,
    mock_event_system: AsyncMock
) -> None:
    """Test project creation with invalid data."""
    mock_event_system.is_connected.return_value = True
    invalid_project = {
        "name": "Test Project"  # Missing required fields
    }
    response = test_client.post(
        "/projects",
        json=invalid_project,
        headers=api_key_header
    )
    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_create_project_no_auth(
    test_client: TestClient,
    sample_project: Dict,
    mock_event_system: AsyncMock
) -> None:
    """Test project creation without authentication."""
    mock_event_system.is_connected.return_value = True
    response = test_client.post(
        "/projects",
        json=sample_project
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"

@pytest.mark.asyncio
async def test_request_tracking(
    test_client: TestClient,
    api_key_header: Dict,
    sample_project: Dict,
    mock_event_system: AsyncMock
) -> None:
    """Test request tracking middleware."""
    # Configure mock
    mock_event_system.is_connected = Mock(return_value=True)
    mock_event_system.connect = AsyncMock()
    mock_event_system.publish = AsyncMock()
    mock_event_system.get_redis = AsyncMock()
    mock_event_system._connected = True
    mock_event_system.redis_client = Mock()
    
    with patch("src.api.core.get_event_system", return_value=mock_event_system), \
         patch("src.api.core._event_system", mock_event_system):  # Also patch the global instance
        # Ensure event system is connected
        await mock_event_system.connect()
        
        # Create project data without deadline
        project_data = {
            "id": sample_project["id"],
            "name": sample_project["name"],
            "description": sample_project["description"],
            "stories": sample_project.get("stories", []),
            "github_url": sample_project.get("github_url")
        }
        
        # Make a request that should be tracked
        response = test_client.post(
            "/projects",
            json=project_data,
            headers={
                **api_key_header,
                "X-Request-ID": "test-request-1"
            }
        )
        assert response.status_code == 200
        
        # Verify request was tracked
        assert response.headers["X-Request-ID"] == "test-request-1"
        assert response.headers["X-Response-Time"] is not None
        
        # Verify event was published with the complete project data
        mock_event_system.publish.assert_called_with(
            "project_created",
            {
                "project_id": project_data["id"],
                "timestamp": ANY,
                "type": "project_created",
                "payload": project_data
            }
        )

@pytest.mark.asyncio
async def test_metrics_endpoint(
    test_client: TestClient,
    api_key_header: Dict,
    mock_event_system: AsyncMock
) -> None:
    """Test the metrics endpoint."""
    mock_event_system.is_connected.return_value = True
    response = test_client.get(
        "/metrics",
        headers=api_key_header
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    metrics_text = response.text
    # Verify some metrics we know are being collected
    assert "python_gc_objects_collected_total" in metrics_text
    assert "python_info" in metrics_text
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds" in metrics_text 