"""Integration tests for health endpoint."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_health_check(async_client: AsyncClient):
    """Test health check endpoint returns healthy status.
    
    Given: The application is running
    When: A GET request is made to /health
    Then: The response should indicate healthy status
    """
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

async def test_health_check_no_auth(async_client: AsyncClient):
    """Test health check endpoint works without authentication.
    
    Given: The application is running with security middleware
    When: A GET request is made to /health without an API key
    Then: The response should still indicate healthy status
    """
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 