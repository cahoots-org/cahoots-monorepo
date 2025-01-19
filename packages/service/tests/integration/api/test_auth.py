"""Integration tests for authentication endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_protected_endpoint_no_key(async_client: AsyncClient):
    """Test protected endpoint requires API key.
    
    Given: The application is running with security middleware
    When: A request is made to a protected endpoint without an API key
    Then: The response should indicate missing API key
    """
    response = await async_client.get("/api/organizations")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}

async def test_protected_endpoint_invalid_key(async_client: AsyncClient):
    """Test protected endpoint validates API key.
    
    Given: The application is running with security middleware
    When: A request is made with an invalid API key
    Then: The response should indicate invalid API key
    """
    response = await async_client.get(
        "/api/organizations",
        headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]

async def test_protected_endpoint_valid_key(async_client: AsyncClient):
    """Test protected endpoint accepts valid API key.
    
    Given: The application is running with security middleware
    When: A request is made with a valid API key
    Then: The request should be processed normally
    """
    response = await async_client.get(
        "/api/organizations",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code in (200, 404)  # Actual response depends on data 