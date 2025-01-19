"""Trello service implementation."""
from typing import Dict, Optional, List
from src.utils.exceptions import ExternalServiceException
from src.utils.async_base import AsyncContextManager
from .client import TrelloClient
from .config import TrelloConfig

class TrelloService(AsyncContextManager):
    """Service for interacting with Trello API."""
    
    def __init__(self, config: TrelloConfig) -> None:
        """Initialize the Trello service.
        
        Args:
            config: TrelloConfig instance for Trello API configuration
        """
        super().__init__()
        self.config = config
        self.client = TrelloClient(
            api_key=config.api_key,
            api_token=config.api_token,
            base_url=config.base_url,
            timeout=config.timeout
        )
        self._resource = self.client
        
    async def create_board(
        self,
        name: str,
        description: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a new board.
        
        Args:
            name: Board name
            description: Board description
            organization_id: Organization ID
            
        Returns:
            Dict with board details including ID
            
        Raises:
            ExternalServiceException: If board creation fails
        """
        response = await self.client.request(
            "POST",
            "/boards",
            json_data={
                "name": name,
                "desc": description or "",
                "idOrganization": organization_id,
                "defaultLists": False
            }
        )
        return {
            "id": response["id"],
            "name": response["name"],
            "url": response["url"]
        }
        
    async def create_list(
        self,
        board_id: str,
        name: str,
        position: str = "bottom"
    ) -> Dict[str, str]:
        """Create a new list in a board.
        
        Args:
            board_id: Board ID
            name: List name
            position: List position (top, bottom, or a positive number)
            
        Returns:
            Dict with list details including ID
            
        Raises:
            ExternalServiceException: If list creation fails
        """
        response = await self.client.request(
            "POST",
            "/lists",
            json_data={
                "name": name,
                "idBoard": board_id,
                "pos": position
            }
        )
        return {
            "id": response["id"],
            "name": response["name"]
        }
        
    async def create_card(
        self,
        list_id: str,
        name: str,
        description: Optional[str] = None,
        position: str = "bottom",
        labels: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Create a new card in a list.
        
        Args:
            list_id: List ID
            name: Card name
            description: Card description
            position: Card position (top, bottom, or a positive number)
            labels: List of label IDs
            
        Returns:
            Dict with card details including ID
            
        Raises:
            ExternalServiceException: If card creation fails
        """
        data = {
            "name": name,
            "desc": description or "",
            "idList": list_id,
            "pos": position
        }
        if labels:
            data["idLabels"] = labels
            
        response = await self.client.request(
            "POST",
            "/cards",
            json_data=data
        )
        return {
            "id": response["id"],
            "name": response["name"],
            "url": response["url"]
        }
        
    async def check_connection(self) -> bool:
        """Check if we can connect to Trello API.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            ExternalServiceException: If connection check fails
        """
        try:
            await self.client.request("GET", "/members/me")
            return True
        except ExternalServiceException:
            return False 