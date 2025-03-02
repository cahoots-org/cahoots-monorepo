"""Trello service implementation."""

from typing import Any, AsyncContextManager, Dict, List, Optional

from cahoots_core.exceptions import ServiceError

from .client import TrelloClient
from .config import TrelloConfig


class TrelloService(AsyncContextManager):
    """Service for interacting with Trello."""

    def __init__(self, config: TrelloConfig):
        """Initialize Trello service.

        Args:
            config: Trello configuration
        """
        self.config = config
        self.client = TrelloClient(config)

    async def __aenter__(self):
        """Enter async context."""
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def create_board(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new Trello board.

        Args:
            name: Board name
            **kwargs: Additional board parameters

        Returns:
            Created board data

        Raises:
            ServiceError: If board creation fails
        """
        try:
            return await self.client.create_board(name, **kwargs)
        except Exception as e:
            raise ServiceError(f"Failed to create Trello board: {str(e)}")

    async def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get Trello board by ID.

        Args:
            board_id: Board ID

        Returns:
            Board data

        Raises:
            ServiceError: If board retrieval fails
        """
        try:
            return await self.client.get_board(board_id)
        except Exception as e:
            raise ServiceError(f"Failed to get Trello board: {str(e)}")

    async def create_list(self, board_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new list on a board.

        Args:
            board_id: Board ID
            name: List name
            **kwargs: Additional list parameters

        Returns:
            Created list data

        Raises:
            ServiceError: If list creation fails
        """
        try:
            return await self.client.create_list(board_id, name, **kwargs)
        except Exception as e:
            raise ServiceError(f"Failed to create Trello list: {str(e)}")

    async def create_card(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new card in a list.

        Args:
            list_id: List ID
            name: Card name
            **kwargs: Additional card parameters

        Returns:
            Created card data

        Raises:
            ServiceError: If card creation fails
        """
        try:
            return await self.client.create_card(list_id, name, **kwargs)
        except Exception as e:
            raise ServiceError(f"Failed to create Trello card: {str(e)}")

    async def get_cards(self, list_id: str) -> List[Dict[str, Any]]:
        """Get all cards in a list.

        Args:
            list_id: List ID

        Returns:
            List of card data

        Raises:
            ServiceError: If card retrieval fails
        """
        try:
            return await self.client.get_cards(list_id)
        except Exception as e:
            raise ServiceError(f"Failed to get Trello cards: {str(e)}")

    async def update_card(self, card_id: str, **kwargs) -> Dict[str, Any]:
        """Update a card.

        Args:
            card_id: Card ID
            **kwargs: Card fields to update

        Returns:
            Updated card data

        Raises:
            ServiceError: If card update fails
        """
        try:
            return await self.client.update_card(card_id, **kwargs)
        except Exception as e:
            raise ServiceError(f"Failed to update Trello card: {str(e)}")

    async def delete_card(self, card_id: str) -> None:
        """Delete a card.

        Args:
            card_id: Card ID

        Raises:
            ServiceError: If card deletion fails
        """
        try:
            await self.client.delete_card(card_id)
        except Exception as e:
            raise ServiceError(f"Failed to delete Trello card: {str(e)}")

    async def create_webhook(self, callback_url: str, id_model: str, **kwargs) -> Dict[str, Any]:
        """Create a webhook for a model.

        Args:
            callback_url: Webhook callback URL
            id_model: ID of model to watch (board, list, card etc)
            **kwargs: Additional webhook parameters

        Returns:
            Created webhook data

        Raises:
            ServiceError: If webhook creation fails
        """
        try:
            return await self.client.create_webhook(callback_url, id_model, **kwargs)
        except Exception as e:
            raise ServiceError(f"Failed to create Trello webhook: {str(e)}")

    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook.

        Args:
            webhook_id: Webhook ID

        Raises:
            ServiceError: If webhook deletion fails
        """
        try:
            await self.client.delete_webhook(webhook_id)
        except Exception as e:
            raise ServiceError(f"Failed to delete Trello webhook: {str(e)}")
