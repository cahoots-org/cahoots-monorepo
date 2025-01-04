"""Abstract base class for task management services."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class TaskManagementService(ABC):
    """Abstract base class for task management services."""
    
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
        
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
        
    @abstractmethod
    async def close(self):
        """Close any open connections."""
        pass
        
    @abstractmethod
    async def create_board(self, name: str, description: str) -> str:
        """Create a new board.
        
        Args:
            name: Board name
            description: Board description
            
        Returns:
            str: Board ID
        """
        pass
        
    @abstractmethod
    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board.
        
        Args:
            board_id: Board ID
            name: List name
            
        Returns:
            str: List ID
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if we can connect to the service.
        
        Returns:
            bool: True if connection successful
        """
        pass 