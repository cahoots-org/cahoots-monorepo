"""Trello implementation of TaskManagementService."""
from typing import Dict, List, Optional
from src.utils.logger import Logger
from src.utils.metrics import track_time, TRELLO_REQUEST_TIME, TRELLO_ERROR_COUNTER
from src.utils.exceptions import ExternalServiceException
from .base import TaskManagementService
from src.services.trello.client import TrelloClient
from src.services.trello.config import TrelloConfig

class TrelloTaskManagementService(TaskManagementService):
    """Trello implementation of TaskManagementService."""
    
    def __init__(self, config: Optional[TrelloConfig] = None) -> None:
        """Initialize the Trello service.
        
        Args:
            config: Optional TrelloConfig instance. If not provided,
                   will be loaded from global config.
        """
        self.config = config or TrelloConfig.from_config()
        self.client = TrelloClient(
            api_key=self.config.api_key,
            api_token=self.config.api_token,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        self.logger = Logger("TrelloTaskManagementService")
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close the Trello client."""
        await self.client.close()

    @track_time(TRELLO_REQUEST_TIME, {"method": "POST", "endpoint": "/boards"})
    async def create_board(self, name: str, description: str) -> str:
        """Create a new Trello board.
        
        Args:
            name: Board name
            description: Board description
            
        Returns:
            str: Board ID
            
        Raises:
            ExternalServiceException: If board creation fails
        """
        try:
            self.logger.info(f"Creating board: {name}")
            response = await self.client.request(
                "POST",
                "/boards",
                params={
                    "name": name,
                    "desc": description,
                    "defaultLists": "false"
                }
            )
            return response["id"]
        except Exception as e:
            TRELLO_ERROR_COUNTER.labels(
                method="POST",
                endpoint="/boards",
                status_code="500"
            ).inc()
            raise ExternalServiceException(
                service="Trello",
                operation="create_board",
                error=str(e)
            )
        
    @track_time(TRELLO_REQUEST_TIME, {"method": "POST", "endpoint": "/lists"})
    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in a board.
        
        Args:
            board_id: Board ID
            name: List name
            
        Returns:
            str: List ID
            
        Raises:
            ExternalServiceException: If list creation fails
        """
        try:
            self.logger.info(f"Creating list '{name}' in board {board_id}")
            response = await self.client.request(
                "POST",
                f"/boards/{board_id}/lists",
                params={"name": name}
            )
            return response["id"]
        except Exception as e:
            TRELLO_ERROR_COUNTER.labels(
                method="POST",
                endpoint="/lists",
                status_code="500"
            ).inc()
            raise ExternalServiceException(
                service="Trello",
                operation="create_list",
                error=str(e)
            )
            
    @track_time(TRELLO_REQUEST_TIME, {"method": "POST", "endpoint": "/cards"})
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
            
        Raises:
            ExternalServiceException: If card creation fails
        """
        try:
            self.logger.info(f"Creating card '{name}' in list '{list_name}'")
            
            # Get list ID
            lists = await self.client.request(
                "GET",
                f"/boards/{board_id}/lists"
            )
            list_id = next(
                (lst["id"] for lst in lists if lst["name"] == list_name),
                None
            )
            if not list_id:
                TRELLO_ERROR_COUNTER.labels(
                    method="GET",
                    endpoint="/lists",
                    status_code="404"
                ).inc()
                raise ExternalServiceException(
                    service="Trello",
                    operation="create_card",
                    error=f"List '{list_name}' not found"
                )
                
            # Create card
            response = await self.client.request(
                "POST",
                "/cards",
                params={
                    "name": name,
                    "desc": description,
                    "idList": list_id
                }
            )
            return response["id"]
        except ExternalServiceException:
            raise
        except Exception as e:
            TRELLO_ERROR_COUNTER.labels(
                method="POST",
                endpoint="/cards",
                status_code="500"
            ).inc()
            raise ExternalServiceException(
                service="Trello",
                operation="create_card",
                error=str(e)
            )
            
    @track_time(TRELLO_REQUEST_TIME, {"method": "GET", "endpoint": "/members/me"})
    async def check_connection(self) -> bool:
        """Check if we can connect to Trello API.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            ExternalServiceException: If connection check fails
        """
        try:
            self.logger.info("Checking Trello connection")
            await self.client.request("GET", "/members/me")
            return True
        except Exception as e:
            TRELLO_ERROR_COUNTER.labels(
                method="GET",
                endpoint="/members/me",
                status_code="500"
            ).inc()
            raise ExternalServiceException(
                service="Trello",
                operation="check_connection",
                error=str(e)
            ) 