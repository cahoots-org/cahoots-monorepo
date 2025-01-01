# src/services/trello_service.py
from typing import Optional, Dict, Any
import httpx
import json
from datetime import datetime
from ..utils.config import Config
from ..utils.logger import Logger
from ..utils.exceptions import ExternalServiceException
from ..utils.metrics import track_time, TRELLO_REQUEST_TIME, TRELLO_ERROR_COUNTER

class TrelloService:
    """Service for interacting with Trello API."""
    
    def __init__(self):
        """Initialize Trello service with configuration and HTTP client."""
        self.config = Config()
        self.logger = Logger("TrelloService")
        
        if not self.config.trello_api_key or not self.config.trello_api_secret:
            raise RuntimeError("TRELLO_API_KEY and TRELLO_API_SECRET environment variables are required")
            
        self.api_key = self.config.trello_api_key
        self.token = self.config.trello_api_secret
        self.base_url = "https://api.trello.com/1"
        
        # Get timeouts from services config
        trello_config = self.config.services["trello"]
        self.timeout = httpx.Timeout(
            connect=float(trello_config.timeout),
            read=float(trello_config.timeout),
            write=float(trello_config.timeout),
            pool=float(trello_config.timeout)
        )
        
        # Initialize HTTP client with retry configuration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json"}
        )
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        
    def _get_auth_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add authentication parameters to the request."""
        auth_params = {
            "key": self.api_key,
            "token": self.token
        }
        if params:
            auth_params.update(params)
        return auth_params
        
    @track_time(TRELLO_REQUEST_TIME)
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to Trello API with error handling and metrics."""
        try:
            response = await self.client.request(
                method,
                f"{endpoint}",
                params=self._get_auth_params(kwargs.get("params")),
                json=kwargs.get("json"),
                timeout=kwargs.get("timeout", self.timeout)
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=e.response.status_code
            ).inc()
            raise ExternalServiceException(
                service_name="Trello",
                operation=f"{method} {endpoint}",
                error=str(e),
                details={"status_code": e.response.status_code}
            )
        except httpx.RequestError as e:
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=0
            ).inc()
            raise ExternalServiceException(
                service_name="Trello",
                operation=f"{method} {endpoint}",
                error=str(e)
            )
            
    async def check_connection(self):
        """Test the Trello connection."""
        await self._make_request("GET", "/members/me/boards")
        
    async def create_board(self, name: str, description: str = "") -> str:
        """Create a new Trello board.
        
        Args:
            name: Board name
            description: Board description
            
        Returns:
            str: Board ID
        """
        self.logger.info(f"Creating board: {name}")
        board = await self._make_request(
            "POST",
            "/boards",
            params={
                "name": name,
                "desc": description,
                "defaultLists": "false"
            }
        )
        return board["id"]
        
    async def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in the board.
        
        Args:
            board_id: Board ID
            name: List name
            
        Returns:
            str: List ID
        """
        self.logger.info(f"Creating list {name} in board {board_id}")
        trello_list = await self._make_request(
            "POST",
            "/lists",
            params={
                "name": name,
                "idBoard": board_id
            }
        )
        return trello_list["id"]
        
    async def create_card(
        self,
        title: str,
        description: str,
        board_id: str,
        list_name: str = "Backlog"
    ) -> str:
        """Create a new card in the specified list.
        
        Args:
            title: Card title
            description: Card description
            board_id: Board ID
            list_name: List name (default: "Backlog")
            
        Returns:
            str: Card ID
        """
        self.logger.info(f"Creating card {title} in board {board_id}")
        
        # Get all lists in the board
        lists = await self._make_request(
            "GET",
            f"/boards/{board_id}/lists"
        )
        
        # Find the target list
        target_list = next((l for l in lists if l["name"] == list_name), None)
        if not target_list:
            raise ExternalServiceException(
                service_name="Trello",
                operation="create_card",
                error=f"List '{list_name}' not found in board",
                details={"board_id": board_id}
            )
            
        # Create the card
        card = await self._make_request(
            "POST",
            "/cards",
            params={
                "name": title,
                "desc": description,
                "idList": target_list["id"],
                "pos": "bottom"
            }
        )
        return card["id"]
        
    async def get_card(self, card_id: str) -> Dict[str, Any]:
        """Get card details.
        
        Args:
            card_id: Card ID
            
        Returns:
            Dict containing card details
        """
        self.logger.info(f"Getting card: {card_id}")
        card = await self._make_request(
            "GET",
            f"/cards/{card_id}",
            params={"fields": "name,desc,idList"}
        )
        
        # Get list info
        list_info = await self._make_request(
            "GET",
            f"/lists/{card['idList']}",
            params={"fields": "name"}
        )
        
        return {
            "id": card["id"],
            "name": card["name"],
            "description": card["desc"],
            "list": {"name": list_info["name"]}
        }
        
    async def update_card(
        self,
        card_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        list_name: Optional[str] = None
    ):
        """Update card details.
        
        Args:
            card_id: Card ID
            title: New card title (optional)
            description: New card description (optional)
            list_name: New list name to move card to (optional)
        """
        self.logger.info(f"Updating card: {card_id}")
        
        # Get current card details
        card = await self._make_request(
            "GET",
            f"/cards/{card_id}",
            params={"fields": "idBoard,idList"}
        )
        
        # Prepare update data
        update_params = {}
        if title is not None:
            update_params["name"] = title
        if description is not None:
            update_params["desc"] = description
            
        if update_params:
            await self._make_request(
                "PUT",
                f"/cards/{card_id}",
                params=update_params
            )
            
        # Move card if list_name provided
        if list_name:
            lists = await self._make_request(
                "GET",
                f"/boards/{card['idBoard']}/lists"
            )
            target_list = next((l for l in lists if l["name"] == list_name), None)
            if not target_list:
                raise ExternalServiceException(
                    service_name="Trello",
                    operation="update_card",
                    error=f"List '{list_name}' not found in board",
                    details={"board_id": card["idBoard"]}
                )
                
            if card["idList"] != target_list["id"]:
                await self._make_request(
                    "PUT",
                    f"/cards/{card_id}/idList",
                    params={"value": target_list["id"]}
                )