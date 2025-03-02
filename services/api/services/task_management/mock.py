"""Mock implementation of task management service for testing."""

import uuid
from typing import Dict, List, Optional

from .base import TaskManagementService


class MockTaskManagementService(TaskManagementService):
    """Mock task management service for testing."""

    def __init__(self):
        """Initialize mock service."""
        self.boards: Dict[str, Dict] = {}
        self.lists: Dict[str, Dict] = {}
        self.cards: Dict[str, Dict] = {}
        self._connected = True

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.close()

    async def close(self):
        """Close the service."""
        self.boards.clear()
        self.lists.clear()
        self.cards.clear()

    def set_connection_status(self, status: bool):
        """Set connection status for testing."""
        self._connected = status

    async def check_connection(self) -> bool:
        """Check if service is connected."""
        return self._connected

    async def create_board(self, name: str, description: str) -> str:
        """Create a new board."""
        board_id = str(uuid.uuid4())
        self.boards[board_id] = {"name": name, "description": description, "lists": []}
        return board_id

    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board."""
        if board_id not in self.boards:
            raise ValueError(f"Board {board_id} not found")

        list_id = str(uuid.uuid4())
        self.lists[list_id] = {"name": name, "board_id": board_id, "cards": []}
        self.boards[board_id]["lists"].append(list_id)
        return list_id

    async def _get_or_create_list(self, board_id: str, list_name: str) -> str:
        """Get existing list by name or create new one."""
        for list_id, list_data in self.lists.items():
            if list_data["board_id"] == board_id and list_data["name"] == list_name:
                return list_id
        return await self.create_list(board_id, list_name)

    async def create_card(self, name: str, description: str, board_id: str, list_name: str) -> str:
        """Create a new card in a list."""
        if board_id not in self.boards:
            raise ValueError(f"Board {board_id} not found")

        list_id = await self._get_or_create_list(board_id, list_name)
        card_id = str(uuid.uuid4())

        self.cards[card_id] = {
            "name": name,
            "description": description,
            "board_id": board_id,
            "list_id": list_id,
        }
        self.lists[list_id]["cards"].append(card_id)
        return card_id
