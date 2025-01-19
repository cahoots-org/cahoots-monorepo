"""Tests for the mock task management service."""
import pytest
from src.services.task_management.mock import MockTaskManagementService

@pytest.fixture
async def mock_service():
    """Create a mock service instance."""
    service = MockTaskManagementService()
    yield service
    await service.close()

async def test_create_board(mock_service):
    """Test creating a board."""
    board_id = await mock_service.create_board("Test Board", "Test Description")
    assert board_id in mock_service.boards
    assert mock_service.boards[board_id]["name"] == "Test Board"
    assert mock_service.boards[board_id]["description"] == "Test Description"
    assert mock_service.boards[board_id]["lists"] == []

async def test_create_list(mock_service):
    """Test creating a list."""
    board_id = await mock_service.create_board("Test Board", "Test Description")
    list_id = await mock_service.create_list(board_id, "Test List")
    
    assert list_id in mock_service.lists
    assert mock_service.lists[list_id]["name"] == "Test List"
    assert mock_service.lists[list_id]["board_id"] == board_id
    assert mock_service.lists[list_id]["cards"] == []
    assert list_id in mock_service.boards[board_id]["lists"]

async def test_create_list_invalid_board(mock_service):
    """Test creating a list with invalid board ID."""
    with pytest.raises(ValueError, match="Board invalid-id not found"):
        await mock_service.create_list("invalid-id", "Test List")

async def test_create_card(mock_service):
    """Test creating a card."""
    board_id = await mock_service.create_board("Test Board", "Test Description")
    list_id = await mock_service.create_list(board_id, "Test List")
    card_id = await mock_service.create_card(
        "Test Card",
        "Test Card Description",
        board_id,
        "Test List"
    )
    
    assert card_id in mock_service.cards
    assert mock_service.cards[card_id]["name"] == "Test Card"
    assert mock_service.cards[card_id]["description"] == "Test Card Description"
    assert mock_service.cards[card_id]["board_id"] == board_id
    assert mock_service.cards[card_id]["list_id"] == list_id
    assert card_id in mock_service.lists[list_id]["cards"]

async def test_create_card_invalid_board(mock_service):
    """Test creating a card with invalid board ID."""
    with pytest.raises(ValueError, match="Board invalid-id not found"):
        await mock_service.create_card(
            "Test Card",
            "Test Card Description",
            "invalid-id",
            "Test List"
        )

async def test_create_card_auto_create_list(mock_service):
    """Test creating a card automatically creates list if not exists."""
    board_id = await mock_service.create_board("Test Board", "Test Description")
    card_id = await mock_service.create_card(
        "Test Card",
        "Test Card Description",
        board_id,
        "New List"
    )
    
    # Find the list that was created
    list_id = mock_service.cards[card_id]["list_id"]
    assert list_id in mock_service.lists
    assert mock_service.lists[list_id]["name"] == "New List"
    assert mock_service.lists[list_id]["board_id"] == board_id
    assert card_id in mock_service.lists[list_id]["cards"]

async def test_check_connection(mock_service):
    """Test connection check."""
    assert await mock_service.check_connection() is True
    
    mock_service.set_connection_status(False)
    assert await mock_service.check_connection() is False
    
    mock_service.set_connection_status(True)
    assert await mock_service.check_connection() is True

async def test_async_context_manager(mock_service):
    """Test using the service as an async context manager."""
    async with mock_service as service:
        assert service is mock_service
        board_id = await service.create_board("Test Board", "Test Description")
        assert board_id in service.boards 