"""Trello API client implementation."""
from typing import AsyncContextManager, Optional, Dict, Any, List
import logging
import aiohttp
from aiohttp import ClientTimeout

from cahoots_core.exceptions import ServiceError
from cahoots_core.services.trello.config import TrelloConfig
from cahoots_core.utils.metrics.timing import track_time

logger = logging.getLogger(__name__)

class TrelloClient(AsyncContextManager):
    """Client for interacting with Trello API."""
    
    def __init__(self, config: TrelloConfig):
        """Initialize Trello client.
        
        Args:
            config: Trello configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Enter async context."""
        self.session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=self.config.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Make request to Trello API.
        
        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request parameters
            
        Returns:
            Response data
            
        Raises:
            ServiceError: If request fails
        """
        if not self.session:
            raise ServiceError("Client session not initialized")
            
        url = f"{self.config.base_url}{path}"
        params = kwargs.pop("params", {})
        params.update({
            "key": self.config.api_key,
            "token": self.config.api_token
        })
        
        try:
            async with self.session.request(method, url, params=params, **kwargs) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise ServiceError(f"Trello API error: {response.status} - {text}")
                return await response.json()
        except aiohttp.ClientError as e:
            raise ServiceError(f"Trello request failed: {str(e)}")
            
    async def create_board(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new board.
        
        Args:
            name: Board name
            **kwargs: Additional board parameters
            
        Returns:
            Created board data
        """
        data = {"name": name, "defaultLists": False, **kwargs}
        return await self.request("POST", "/boards", json=data)
        
    async def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get board by ID.
        
        Args:
            board_id: Board ID
            
        Returns:
            Board data
        """
        return await self.request("GET", f"/boards/{board_id}")
        
    async def create_list(self, board_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new list on a board.
        
        Args:
            board_id: Board ID
            name: List name
            **kwargs: Additional list parameters
            
        Returns:
            Created list data
        """
        data = {"name": name, "idBoard": board_id, **kwargs}
        return await self.request("POST", "/lists", json=data)
        
    async def create_card(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new card in a list.
        
        Args:
            list_id: List ID
            name: Card name
            **kwargs: Additional card parameters
            
        Returns:
            Created card data
        """
        data = {"name": name, "idList": list_id, **kwargs}
        return await self.request("POST", "/cards", json=data)
        
    async def get_cards(self, list_id: str) -> List[Dict[str, Any]]:
        """Get all cards in a list.
        
        Args:
            list_id: List ID
            
        Returns:
            List of card data
        """
        return await self.request("GET", f"/lists/{list_id}/cards")
        
    async def update_card(self, card_id: str, **kwargs) -> Dict[str, Any]:
        """Update a card.
        
        Args:
            card_id: Card ID
            **kwargs: Card fields to update
            
        Returns:
            Updated card data
        """
        return await self.request("PUT", f"/cards/{card_id}", json=kwargs)
        
    async def delete_card(self, card_id: str) -> None:
        """Delete a card.
        
        Args:
            card_id: Card ID
        """
        await self.request("DELETE", f"/cards/{card_id}")
        
    async def create_webhook(self, callback_url: str, id_model: str, **kwargs) -> Dict[str, Any]:
        """Create a webhook for a model.
        
        Args:
            callback_url: Webhook callback URL
            id_model: ID of model to watch (board, list, card etc)
            **kwargs: Additional webhook parameters
            
        Returns:
            Created webhook data
        """
        data = {
            "callbackURL": callback_url,
            "idModel": id_model,
            **kwargs
        }
        return await self.request("POST", "/webhooks", json=data)
        
    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook.
        
        Args:
            webhook_id: Webhook ID
        """
        await self.request("DELETE", f"/webhooks/{webhook_id}") 