"""Trello implementation of TaskManagementService."""

from typing import AsyncContextManager

from api.dependencies import ServiceDeps
from services.task_management.base import TaskManagementService

from cahoots_core.exceptions import ServiceError
from cahoots_core.services.trello.service import TrelloService


class TrelloTaskManagementService(TaskManagementService, AsyncContextManager):
    """Trello implementation of TaskManagementService."""

    def __init__(self, deps: ServiceDeps):
        """Initialize the Trello service.

        Args:
            deps: Service dependencies including configuration
        """
        super().__init__()
        self.trello = TrelloService(deps.settings.trello)
        self._resource = self.trello

    async def create_board(self, name: str, description: str) -> str:
        """Create a new board.

        Args:
            name: Board name
            description: Board description

        Returns:
            str: Board ID

        Raises:
            ServiceError: If board creation fails
        """
        try:
            response = await self.trello.create_board(name, description)
            return response.get("id")
        except Exception as e:
            raise ServiceError(
                service="trello",
                operation="create_board",
                message=f"Failed to create board '{name}'",
            ) from e

    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board.

        Args:
            board_id: Board ID
            name: List name

        Returns:
            str: List ID

        Raises:
            ServiceError: If list creation fails
        """
        try:
            response = await self.trello.create_list(board_id, name)
            return response["id"]
        except Exception as e:
            raise ServiceError(
                service="trello",
                operation="create_list",
                message=f"Failed to create list '{name}' in board {board_id}",
            ) from e

    async def create_card(
        self, name: str, description: str, board_id: str, list_name: str = "Backlog"
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
        response = await self.trello.create_card(name, description, board_id, list_name)
        return response.get("id")

    async def check_connection(self) -> bool:
        """Check if we can connect to Trello API."""
        try:
            return await self.trello.check_connection()
        except Exception as e:
            raise ServiceError(
                message=f"Failed to connect to Trello API: {str(e)}",
                service="trello",
                operation="check_connection",
            )
