"""Tests for TrelloClient."""
import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from src.services.trello.client import TrelloClient
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
async def client() -> TrelloClient:
    """Create test client."""
    client = TrelloClient(
        api_key="test_key",
        api_token="test_token"
    )
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_request_success(client: TrelloClient) -> None:
    """Test successful request."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"id": "123"})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        response = await client.request("GET", "/test")
        assert response == {"id": "123"}

@pytest.mark.asyncio
async def test_request_error(client: TrelloClient) -> None:
    """Test request error handling."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request")
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        with pytest.raises(ExternalServiceException, match="Trello API request failed: Bad Request"):
            await client.request("GET", "/test")

@pytest.mark.asyncio
async def test_session_management(client: TrelloClient) -> None:
    """Test session creation and cleanup."""
    # Test session creation
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"id": "123"})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        assert client._session is None
        await client.request("GET", "/test")
        assert client._session is not None

        # Test session reuse
        await client.request("GET", "/test")
        assert client._session is not None

        # Test session cleanup
        await client.close()
        assert client._session is None

@pytest.mark.asyncio
async def test_network_errors(client: TrelloClient) -> None:
    """Test handling of network errors."""
    with patch("aiohttp.ClientSession.request", side_effect=aiohttp.ClientError("Network Error")):
        with pytest.raises(ExternalServiceException, match="Trello API request failed: Network Error"):
            await client.request("GET", "/test")

    with patch("aiohttp.ClientSession.request", side_effect=TimeoutError("Timeout")):
        with pytest.raises(ExternalServiceException, match="Unexpected error: Timeout"):
            await client.request("GET", "/test")

@pytest.mark.asyncio
async def test_request_params(client: TrelloClient) -> None:
    """Test request parameter handling."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response) as mock_request:
        await client.request(
            "POST",
            "/test",
            params={"custom": "param"},
            json_data={"data": "value"}
        )
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args[1]
        assert call_args["params"] == {
            "custom": "param",
            "key": "test_key",
            "token": "test_token"
        }
        assert call_args["json"] == {"data": "value"}

@pytest.mark.asyncio
async def test_mock_status_handling(client: TrelloClient) -> None:
    """Test handling of mock status values."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Mock Error")
    mock_response.json = AsyncMock(return_value={})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        with pytest.raises(ExternalServiceException, match="Trello API request failed: Mock Error"):
            await client.request("GET", "/test") 

@pytest.mark.asyncio
async def test_value_error_handling(client: TrelloClient) -> None:
    """Test handling of ValueError during response parsing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        with pytest.raises(ExternalServiceException, match="Unexpected error: Invalid JSON"):
            await client.request("GET", "/test") 

@pytest.mark.asyncio
async def test_mock_status_with_return_value(client: TrelloClient) -> None:
    """Test handling of mock status with _mock_return_value."""
    mock_response = AsyncMock()
    mock_response.status = MagicMock()
    mock_response.status._mock_return_value = 200
    mock_response.status.__int__ = Mock(side_effect=ValueError)
    mock_response.json = AsyncMock(return_value={"id": "123"})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        response = await client.request("GET", "/test")
        assert response == {"id": "123"}

    # Test error case
    mock_response.status._mock_return_value = 400
    mock_response.text = AsyncMock(return_value="Mock Error")

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        with pytest.raises(ExternalServiceException, match="Trello API request failed: Mock Error"):
            await client.request("GET", "/test") 