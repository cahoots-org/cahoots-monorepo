"""Tests for the main API endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.main import app
from typing import Dict, Generator
import json
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio

async def test_health_check(test_client: TestClient):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "redis_connected" in data

async def test_create_project_unauthorized(test_client: TestClient, sample_project: Dict):
    """Test project creation without API key."""
    response = test_client.post("/projects", json=sample_project)
    assert response.status_code == 401

async def test_create_project_success(
    test_client: TestClient,
    sample_project: Dict,
    api_key_header: Dict,
    mock_event_system: AsyncMock
):
    """Test successful project creation."""
    # Configure mock
    mock_event_system.is_connected.return_value = True
    mock_event_system.publish.return_value = None
    
    response = test_client.post(
        "/projects",
        json=sample_project,
        headers=api_key_header
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_project["id"]
    assert data["status"] == "success"
    
    # Verify event was published
    mock_event_system.publish.assert_called_once()
    call_args = mock_event_system.publish.call_args[0]
    assert call_args[0] == "projects"
    published_msg = call_args[1]
    assert published_msg["id"] == sample_project["id"]

async def test_create_project_invalid_data(
    test_client: TestClient,
    api_key_header: Dict
):
    """Test project creation with invalid data."""
    invalid_project = {
        "name": "Test Project"  # Missing required fields
    }
    response = test_client.post(
        "/projects",
        json=invalid_project,
        headers=api_key_header
    )
    assert response.status_code == 422

async def test_metrics_endpoint(test_client: TestClient):
    """Test the metrics endpoint."""
    response = test_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

async def test_request_tracking(
    test_client: TestClient,
    api_key_header: Dict,
    sample_project: Dict
):
    """Test request tracking middleware."""
    # Make a request that should be tracked
    response = test_client.post(
        "/projects",
        json=sample_project,
        headers={
            **api_key_header,
            "X-Request-ID": "test-request-1"
        }
    )
    assert response.status_code == 200
    
    # Verify response headers
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == "test-request-1"
    
    # Check metrics endpoint for the tracked request
    metrics_response = test_client.get("/metrics")
    metrics_data = metrics_response.text
    
    # Verify request count metric exists
    assert 'http_requests_total{' in metrics_data
    assert 'method="POST"' in metrics_data
    assert 'endpoint="/projects"' in metrics_data
    
    # Verify latency metric exists
    assert 'http_request_duration_seconds' in metrics_data 