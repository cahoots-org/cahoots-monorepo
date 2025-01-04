"""Tests for TrelloService."""
import pytest
from unittest.mock import AsyncMock
from src.services.trello.service import TrelloService
from src.services.trello.config import TrelloConfig
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
def config() -> TrelloConfig:
    """Create a test config."""
    return TrelloConfig(
        api_key="test_key",
        api_token="test_token",
        base_url="https://test.trello.com",
        timeout=5
    )

@pytest.fixture
async def service(config: TrelloConfig) -> TrelloService:
    """Create a test service instance."""
    service = TrelloService(config=config)
    service.client.request = AsyncMock()
    yield service
    await service.close()

@pytest.mark.asyncio
async def test_create_board(service: TrelloService) -> None:
    """Test board creation."""
    mock_response = {"id": "test_board_id"}
    service.client.request.return_value = mock_response
    
    board_id = await service.create_board("Test Board", "Test Description")
    
    assert board_id == "test_board_id"
    service.client.request.assert_called_once_with(
        "POST",
        "/boards",
        params={
            "name": "Test Board",
            "desc": "Test Description",
            "defaultLists": "false"
        }
    )

@pytest.mark.asyncio
async def test_create_list(service: TrelloService) -> None:
    """Test list creation."""
    mock_response = {"id": "test_list_id"}
    service.client.request.return_value = mock_response
    
    list_id = await service.create_list("test_board_id", "Test List")
    
    assert list_id == "test_list_id"
    service.client.request.assert_called_once_with(
        "POST",
        f"/boards/test_board_id/lists",
        params={"name": "Test List"}
    )

@pytest.mark.asyncio
async def test_create_card(service: TrelloService) -> None:
    """Test card creation."""
    lists_response = [
        {"id": "list123", "name": "Backlog"},
        {"id": "list456", "name": "In Progress"}
    ]
    card_response = {"id": "card123"}
    
    service.client.request.side_effect = [
        lists_response,
        card_response
    ]
    
    card_id = await service.create_card(
        "Test Card",
        "Test Description",
        "board123",
        "Backlog"
    )
    
    assert card_id == "card123"
    assert service.client.request.call_count == 2
    
    service.client.request.assert_any_call(
        "GET",
        "/boards/board123/lists"
    )
    
    service.client.request.assert_any_call(
        "POST",
        "/cards",
        params={
            "name": "Test Card",
            "desc": "Test Description",
            "idList": "list123"
        }
    )

@pytest.mark.asyncio
async def test_create_card_list_not_found(service: TrelloService) -> None:
    """Test card creation with non-existent list."""
    service.client.request.return_value = []
    
    with pytest.raises(ExternalServiceException, match="Trello service error during create_card: List 'Backlog' not found"):
        await service.create_card(
            "Test Card",
            "Test Description",
            "board123",
            "Backlog"
        )

@pytest.mark.asyncio
async def test_check_connection_success(service: TrelloService) -> None:
    """Test successful connection check."""
    service.client.request.return_value = {"id": "test_user"}
    
    result = await service.check_connection()
    assert result is True
    service.client.request.assert_called_once_with("GET", "/members/me")

@pytest.mark.asyncio
async def test_check_connection_failure(service: TrelloService) -> None:
    """Test failed connection check."""
    service.client.request.side_effect = Exception("Connection failed")
    
    with pytest.raises(ExternalServiceException, match="Trello service error during check_connection: Connection failed"):
        await service.check_connection() 