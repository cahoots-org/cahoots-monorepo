"""Mock implementation of TaskManagementService for testing."""
from typing import Dict, List, Optional
from uuid import uuid4
from .base import TaskManagementService

class MockTaskManagementService(TaskManagementService):
    """Mock implementation of TaskManagementService for testing."""
    
    def __init__(self) -> None:
        """Initialize the mock service."""
        self.boards: Dict[str, Dict] = {}  # board_id -> board data
        self.lists: Dict[str, Dict] = {}   # list_id -> list data
        self.cards: Dict[str, Dict] = {}   # card_id -> card data
        self.is_connected = True
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close the mock service."""
        pass
        
    async def create_board(self, name: str, description: str) -> str:
        """Create a new board.
        
        Args:
            name: Board name
            description: Board description
            
        Returns:
            str: Board ID
        """
        board_id = str(uuid4())
        self.boards[board_id] = {
            "id": board_id,
            "name": name,
            "description": description,
            "lists": []
        }
        return board_id
        
    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board.
        
        Args:
            board_id: Board ID
            name: List name
            
        Returns:
            str: List ID
        """
        if board_id not in self.boards:
            raise ValueError(f"Board {board_id} not found")
            
        list_id = str(uuid4())
        self.lists[list_id] = {
            "id": list_id,
            "name": name,
            "board_id": board_id,
            "cards": []
        }
        self.boards[board_id]["lists"].append(list_id)
        return list_id
        
    async def create_card(
        self,
        name: str,
        description: str,
        board_id: str,
        list_name: str = "Backlog"
    ) -> str:
        """Create a new card in a list.
        
        Args:
            name: Card name
            description: Card description
            board_id: Board ID
            list_name: Name of the list to add card to (default: Backlog)
            
        Returns:
            str: Card ID
        """
        if board_id not in self.boards:
            raise ValueError(f"Board {board_id} not found")
            
        # Find list by name
        target_list_id = None
        for list_id in self.boards[board_id]["lists"]:
            if self.lists[list_id]["name"] == list_name:
                target_list_id = list_id
                break
                
        if not target_list_id:
            target_list_id = await self.create_list(board_id, list_name)
            
        card_id = str(uuid4())
        self.cards[card_id] = {
            "id": card_id,
            "name": name,
            "description": description,
            "list_id": target_list_id,
            "board_id": board_id
        }
        self.lists[target_list_id]["cards"].append(card_id)
        return card_id
        
    async def check_connection(self) -> bool:
        """Check if we can connect to the service.
        
        Returns:
            bool: True if connection successful
        """
        return self.is_connected
        
    def set_connection_status(self, is_connected: bool):
        """Set the connection status for testing.
        
        Args:
            is_connected: Whether the service should appear connected
        """
        self.is_connected = is_connected 