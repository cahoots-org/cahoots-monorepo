"""Tests for TrelloTaskManagementService."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.services.task_management.trello import TrelloTaskManagementService
from src.services.trello.config import TrelloConfig
from src.core.dependencies import ServiceDeps

@pytest.fixture
def mock_trello_config():
    """Create a mock Trello config."""
    return TrelloConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_token="test-token",
        organization_id="test-org",
        board_template_id="test-board",
        timeout=30,
        retry_attempts=3,
        retry_delay=1
    )

@pytest.fixture
def mock_deps(mock_trello_config):
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.settings = MagicMock()
    deps.settings.trello = mock_trello_config
    return deps

@pytest.fixture
async def trello_service(mock_deps):
    """Create a Trello service instance with mocked service."""
    with patch("src.services.task_management.trello.TrelloService") as mock_service_cls:
        mock_service = AsyncMock()
        mock_service_cls.return_value = mock_service
        service = TrelloTaskManagementService(deps=mock_deps)
        yield service, mock_service

@pytest.mark.asyncio
async def test_create_board(trello_service):
    """Test creating a board."""
    service, mock_service = trello_service
    mock_service.create_board.return_value = {"id": "board-123"}
    
    board_id = await service.create_board("Test Board", "Test Description")
    
    assert board_id == "board-123"
    mock_service.create_board.assert_called_once_with(
        "Test Board",
        "Test Description"
    )

@pytest.mark.asyncio
async def test_create_board_error(trello_service):
    """Test error handling when creating a board."""
    service, mock_service = trello_service
    mock_service.create_board.side_effect = Exception("API error")
    
    with pytest.raises(Exception):
        await service.create_board("Test Board", "Test Description")

@pytest.mark.asyncio
async def test_create_list(trello_service):
    """Test creating a list."""
    service, mock_service = trello_service
    mock_service.create_list.return_value = {"id": "list-123"}
    
    list_id = await service.create_list("board-123", "Test List")
    
    assert list_id == "list-123"
    mock_service.create_list.assert_called_once_with(
        "board-123",
        "Test List"
    )

@pytest.mark.asyncio
async def test_create_list_error(trello_service):
    """Test error handling when creating a list."""
    service, mock_service = trello_service
    mock_service.create_list.side_effect = Exception("API error")
    
    with pytest.raises(Exception):
        await service.create_list("board-123", "Test List")

@pytest.mark.asyncio
async def test_create_card(trello_service):
    """Test creating a card."""
    service, mock_service = trello_service
    mock_service.create_card.return_value = {"id": "card-123"}
    
    card_id = await service.create_card(
        "Test Card",
        "Test Description",
        "board-123",
        "Test List"
    )
    
    assert card_id == "card-123"
    mock_service.create_card.assert_called_once_with(
        "Test Card",
        "Test Description",
        "board-123",
        "Test List"
    )

@pytest.mark.asyncio
async def test_create_card_error(trello_service):
    """Test error handling when creating a card."""
    service, mock_service = trello_service
    mock_service.create_card.side_effect = Exception("API error")
    
    with pytest.raises(Exception):
        await service.create_card(
            "Test Card",
            "Test Description",
            "board-123",
            "Test List"
        )

@pytest.mark.asyncio
async def test_create_card_list_not_found(trello_service):
    """Test creating a card when list is not found."""
    service, mock_service = trello_service
    mock_service.create_card.side_effect = Exception("List not found")
    
    with pytest.raises(Exception):
        await service.create_card(
            "Test Card",
            "Test Description",
            "board-123",
            "Non-existent List"
        )

@pytest.mark.asyncio
async def test_check_connection(trello_service):
    """Test checking connection."""
    service, mock_service = trello_service
    mock_service.check_connection.return_value = True
    
    result = await service.check_connection()
    
    assert result is True
    mock_service.check_connection.assert_called_once()

@pytest.mark.asyncio
async def test_check_connection_error(trello_service):
    """Test error handling when checking connection."""
    service, mock_service = trello_service
    mock_service.check_connection.side_effect = Exception("Connection error")
    
    with pytest.raises(Exception):
        await service.check_connection()

@pytest.mark.asyncio
async def test_async_context_manager(trello_service):
    """Test async context manager."""
    service, mock_service = trello_service
    
    async with service:
        await service.check_connection()
        
    mock_service.close.assert_called_once() 