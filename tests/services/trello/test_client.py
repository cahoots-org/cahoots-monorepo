"""Tests for the TrelloClient class."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from src.services.trello.client import TrelloClient
from src.utils.base_logger import BaseLogger
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
def client() -> TrelloClient:
    """Create a TrelloClient instance."""
    logger = BaseLogger("TrelloClient")
    return TrelloClient("test_key", "test_token", logger)

@pytest.mark.asyncio
async def test_request_success(client: TrelloClient) -> None:
    """Test successful request."""
    expected_response = {"id": "test_id"}
    
    # Create mock response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = Mock(return_value=expected_response)  # Not async since httpx returns a sync value
    
    # Mock the httpx client with async request
    mock_request = AsyncMock(return_value=mock_response)
    with patch.object(client._client, 'request', mock_request):
        result = await client.request(
            "GET",
            "/test",
            params={"extra": "param"},
            json_data={"test": "data"}
        )
    
    assert result == expected_response
    mock_request.assert_awaited_once()
    mock_response.raise_for_status.assert_awaited_once()
    mock_response.json.assert_called_once()

@pytest.mark.asyncio
async def test_request_error(client: TrelloClient) -> None:
    """Test request with error response."""
    # Create mock response that raises an error
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock(side_effect=httpx.HTTPError("Test error"))
    
    # Mock the httpx client with async request
    mock_request = AsyncMock(return_value=mock_response)
    with patch.object(client._client, 'request', mock_request):
        with pytest.raises(ExternalServiceException) as exc_info:
            await client.request("GET", "/test")
    
    assert "Test error" in str(exc_info.value)
    mock_request.assert_awaited_once()
    mock_response.raise_for_status.assert_awaited_once() 