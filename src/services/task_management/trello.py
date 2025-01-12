"""Trello implementation of TaskManagementService."""
from src.utils.exceptions import ExternalServiceException
from src.utils.async_base import AsyncContextManager
from .base import TaskManagementService
from src.services.trello.service import TrelloService
from src.core.dependencies import ServiceDeps

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
        """
        response = await self.trello.create_board(name, description)
        return response["id"]
        
    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board.
        
        Args:
            board_id: Board ID
            name: List name
            
        Returns:
            str: List ID
        """
        response = await self.trello.create_list(board_id, name)
        return response["id"]
        
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
        response = await self.trello.create_card(name, description, board_id, list_name)
        return response["id"]

    async def check_connection(self) -> bool:
        """Check if we can connect to Trello API.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            ExternalServiceException: If connection check fails
        """
        return await self.trello.check_connection() 