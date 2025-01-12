"""Tests for TrelloService."""
import pytest
from unittest.mock import AsyncMock, patch, Mock
from src.services.trello.service import TrelloService
from src.services.trello.config import TrelloConfig
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
def trello_config() -> TrelloConfig:
    """Create test Trello config."""
    return TrelloConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_token="test-token"
    )

@pytest.fixture
async def trello_service(trello_config: TrelloConfig) -> TrelloService:
    """Create test Trello service."""
    service = TrelloService(config=trello_config)
    yield service
    await service.close()

@pytest.mark.asyncio
async def test_init_with_config(trello_config: TrelloConfig) -> None:
    """Test initializing service with config."""
    service = TrelloService(config=trello_config)
    assert service.config == trello_config
    assert service.client.api_key == trello_config.api_key
    assert service.client.api_token == trello_config.api_token
    assert service.client.base_url == trello_config.url
    assert service.client.timeout == trello_config.timeout

@pytest.mark.asyncio
async def test_create_board(trello_service: TrelloService) -> None:
    """Test creating a board."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": "test-board-id",
        "name": "Test Board",
        "url": "https://trello.com/b/test-board-id"
    })
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        board = await trello_service.create_board(
            name="Test Board",
            description="Test Description"
        )
        assert board["id"] == "test-board-id"
        assert board["name"] == "Test Board"
        assert board["url"] == "https://trello.com/b/test-board-id"

@pytest.mark.asyncio
async def test_create_list(trello_service: TrelloService) -> None:
    """Test creating a list."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": "test-list-id",
        "name": "Test List"
    })
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        list_data = await trello_service.create_list(
            board_id="test-board-id",
            name="Test List",
            position="top"
        )
        assert list_data["id"] == "test-list-id"
        assert list_data["name"] == "Test List"

@pytest.mark.asyncio
async def test_create_card(trello_service: TrelloService) -> None:
    """Test creating a card."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": "test-card-id",
        "name": "Test Card",
        "url": "https://trello.com/c/test-card-id"
    })
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        card = await trello_service.create_card(
            list_id="test-list-id",
            name="Test Card",
            description="Test Description",
            position="top",
            labels=["label1", "label2"]
        )
        assert card["id"] == "test-card-id"
        assert card["name"] == "Test Card"
        assert card["url"] == "https://trello.com/c/test-card-id"

@pytest.mark.asyncio
async def test_create_card_no_labels(trello_service: TrelloService) -> None:
    """Test creating a card without labels."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": "test-card-id",
        "name": "Test Card",
        "url": "https://trello.com/c/test-card-id"
    })
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response) as mock_request:
        card = await trello_service.create_card(
            list_id="test-list-id",
            name="Test Card",
            description="Test Description",
            position="top"
        )
        assert card["id"] == "test-card-id"
        assert card["name"] == "Test Card"
        assert card["url"] == "https://trello.com/c/test-card-id"
        
        # Verify labels were not included in request
        call_args = mock_request.call_args[1]
        assert "idLabels" not in call_args["json"]

@pytest.mark.asyncio
async def test_check_connection(trello_service: TrelloService) -> None:
    """Test checking connection."""
    # Test successful connection
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"id": "test-user"})
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        assert await trello_service.check_connection() is True

    # Test failed connection
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.text = AsyncMock(return_value="Unauthorized")
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        assert await trello_service.check_connection() is False

@pytest.mark.asyncio
async def test_service_error_handling(trello_service: TrelloService) -> None:
    """Test error handling."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="API Error")
    mock_response.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        with pytest.raises(ExternalServiceException, match="Trello API request failed: API Error"):
            await trello_service.create_board("Test Board") 