"""Tests for the Trello task management service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.task_management.trello import TrelloTaskManagementService
from src.services.trello.config import TrelloConfig
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
def mock_config():
    """Create a mock Trello config."""
    return TrelloConfig(
        api_key="test-key",
        api_token="test-token",
        base_url="https://api.trello.test",
        timeout=30
    )

@pytest.fixture
async def trello_service(mock_config):
    """Create a Trello service instance with mocked client."""
    with patch("src.services.task_management.trello.TrelloClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        service = TrelloTaskManagementService(mock_config)
        yield service, mock_client
        await service.close()

async def test_create_board(trello_service):
    """Test creating a board."""
    service, mock_client = trello_service
    mock_client.request.return_value = {"id": "board-123"}
    
    board_id = await service.create_board("Test Board", "Test Description")
    
    assert board_id == "board-123"
    mock_client.request.assert_called_once_with(
        "POST",
        "/boards",
        params={
            "name": "Test Board",
            "desc": "Test Description",
            "defaultLists": "false"
        }
    )

async def test_create_board_error(trello_service):
    """Test error handling when creating a board."""
    service, mock_client = trello_service
    mock_client.request.side_effect = Exception("API error")
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await service.create_board("Test Board", "Test Description")
    
    assert str(exc_info.value) == "Trello service error during create_board: API error"

async def test_create_list(trello_service):
    """Test creating a list."""
    service, mock_client = trello_service
    mock_client.request.return_value = {"id": "list-123"}
    
    list_id = await service.create_list("board-123", "Test List")
    
    assert list_id == "list-123"
    mock_client.request.assert_called_once_with(
        "POST",
        "/boards/board-123/lists",
        params={"name": "Test List"}
    )

async def test_create_list_error(trello_service):
    """Test error handling when creating a list."""
    service, mock_client = trello_service
    mock_client.request.side_effect = Exception("API error")
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await service.create_list("board-123", "Test List")
    
    assert str(exc_info.value) == "Trello service error during create_list: API error"

async def test_create_card(trello_service):
    """Test creating a card."""
    service, mock_client = trello_service
    mock_client.request.side_effect = [
        # First call - get lists
        [{"id": "list-123", "name": "Test List"}],
        # Second call - create card
        {"id": "card-123"}
    ]
    
    card_id = await service.create_card(
        "Test Card",
        "Test Card Description",
        "board-123",
        "Test List"
    )
    
    assert card_id == "card-123"
    assert mock_client.request.call_count == 2
    mock_client.request.assert_any_call(
        "GET",
        "/boards/board-123/lists"
    )
    mock_client.request.assert_any_call(
        "POST",
        "/cards",
        params={
            "name": "Test Card",
            "desc": "Test Card Description",
            "idList": "list-123"
        }
    )

async def test_create_card_list_not_found(trello_service):
    """Test error handling when list not found."""
    service, mock_client = trello_service
    mock_client.request.return_value = []  # No lists found
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await service.create_card(
            "Test Card",
            "Test Card Description",
            "board-123",
            "Test List"
        )
    
    assert str(exc_info.value) == "Trello service error during create_card: List 'Test List' not found"

async def test_create_card_error(trello_service):
    """Test error handling when creating a card."""
    service, mock_client = trello_service
    mock_client.request.side_effect = Exception("API error")
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await service.create_card(
            "Test Card",
            "Test Card Description",
            "board-123",
            "Test List"
        )
    
    assert str(exc_info.value) == "Trello service error during create_card: API error"

async def test_check_connection(trello_service):
    """Test connection check."""
    service, mock_client = trello_service
    mock_client.request.return_value = {"id": "user-123"}
    
    assert await service.check_connection() is True
    mock_client.request.assert_called_once_with("GET", "/members/me")

async def test_check_connection_error(trello_service):
    """Test error handling during connection check."""
    service, mock_client = trello_service
    mock_client.request.side_effect = Exception("API error")
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await service.check_connection()
    
    assert str(exc_info.value) == "Trello service error during check_connection: API error"

async def test_async_context_manager(trello_service):
    """Test using the service as an async context manager."""
    service, mock_client = trello_service
    mock_client.request.return_value = {"id": "board-123"}
    
    async with service as svc:
        assert svc is service
        board_id = await svc.create_board("Test Board", "Test Description")
        assert board_id == "board-123"
    
    mock_client.close.assert_called_once() 