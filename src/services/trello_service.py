# src/services/trello_service.py
import requests
import json
from typing import Optional, Dict, Any
from ..utils.config import Config
from ..utils.logger import Logger

class TrelloService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("TrelloService")
        if not self.config.trello_api_key or not self.config.trello_api_secret:
            raise RuntimeError("TRELLO_API_KEY and TRELLO_API_SECRET environment variables are required for Trello integration")
        self.api_key = self.config.trello_api_key
        self.token = self.config.trello_api_secret
        self.base_url = "https://api.trello.com/1"
        self.powerup_id = "676fd1d34043fbb17d042976"  # Your Power-Up ID
        
    def _get_auth_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add authentication parameters to the request"""
        auth_params = {
            "key": self.api_key,
            "token": self.token
        }
        if params:
            auth_params.update(params)
        return auth_params
        
    def check_connection(self):
        """Test the Trello connection"""
        response = requests.get(
            f"{self.base_url}/members/me/boards",
            params=self._get_auth_params()
        )
        response.raise_for_status()
        
    def create_board(self, name: str, description: str = "") -> str:
        """Create a new Trello board"""
        try:
            self.logger.info(f"Creating board: {name}")
            response = requests.post(
                f"{self.base_url}/boards",
                params=self._get_auth_params({
                    "name": name,
                    "desc": description,
                    "defaultLists": "false"
                })
            )
            response.raise_for_status()
            board = response.json()
            
            # Try to configure Power-Up but don't fail if it doesn't work
            try:
                self._configure_power_up(board["id"])
            except Exception as e:
                self.logger.warning(f"Power-Up configuration skipped: {str(e)}")
            
            return board["id"]
        except Exception as e:
            self.logger.error(f"Failed to create board: {str(e)}")
            raise
        
    def create_list(self, board_id: str, name: str) -> str:
        """Create a new list in the board"""
        try:
            self.logger.info(f"Creating list {name} in board {board_id}")
            response = requests.post(
                f"{self.base_url}/lists",
                params=self._get_auth_params({
                    "name": name,
                    "idBoard": board_id
                })
            )
            response.raise_for_status()
            trello_list = response.json()
            
            # Try to store list metadata but don't fail if it doesn't work
            try:
                self._store_list_metadata(board_id, trello_list["id"], name)
            except Exception as e:
                self.logger.warning(f"List metadata storage skipped: {str(e)}")
            
            return trello_list["id"]
        except Exception as e:
            self.logger.error(f"Failed to create list: {str(e)}")
            raise
        
    def create_card(self, title: str, description: str, board_id: str, list_name: str = "Backlog") -> str:
        """Create a new card in the specified list"""
        try:
            self.logger.info(f"Creating card {title} in board {board_id}")
            
            # Get all lists in the board
            lists_response = requests.get(
                f"{self.base_url}/boards/{board_id}/lists",
                params=self._get_auth_params()
            )
            lists_response.raise_for_status()
            lists = lists_response.json()
            
            # Find the target list
            target_list = next(l for l in lists if l["name"] == list_name)
            
            # Create the card
            response = requests.post(
                f"{self.base_url}/cards",
                params=self._get_auth_params({
                    "name": title,
                    "desc": description,
                    "idList": target_list["id"]
                })
            )
            response.raise_for_status()
            card = response.json()
            
            # Try to add Power-Up data but don't fail if it doesn't work
            try:
                self._add_power_up_data(card["id"])
            except Exception as e:
                self.logger.warning(f"Power-Up data addition skipped: {str(e)}")
            
            return card["id"]
        except Exception as e:
            self.logger.error(f"Failed to create card: {str(e)}")
            raise
        
    def get_card(self, card_id: str) -> dict:
        self.logger.info(f"Getting card: {card_id}")
        response = requests.get(
            f"{self.base_url}/cards/{card_id}",
            params=self._get_auth_params({
                "fields": "name,desc,idList"
            })
        )
        response.raise_for_status()
        card = response.json()
        
        # Get list info
        list_response = requests.get(
            f"{self.base_url}/lists/{card['idList']}",
            params=self._get_auth_params({
                "fields": "name"
            })
        )
        list_response.raise_for_status()
        list_info = list_response.json()
        
        result = {
            "id": card["id"],
            "name": card["name"],
            "desc": card["desc"],
            "list": {"name": list_info["name"]}
        }
        
        try:
            # Try to get Power-Up data
            plugin_response = requests.get(
                f"{self.base_url}/cards/{card_id}/pluginData",
                params=self._get_auth_params()
            )
            plugin_response.raise_for_status()
            plugin_data = plugin_response.json()
            
            if plugin_data:
                result["status"] = plugin_data[0].get("value", {}).get("status", "unknown")
        except Exception as e:
            self.logger.warning(f"Failed to get Power-Up data: {str(e)}")
            result["status"] = "unknown"
            
        return result
        
    def update_card(self, card_id: str, title: str, description: str, status: str):
        self.logger.info(f"Updating card: {card_id}")
        # Get card's board ID first
        response = requests.get(
            f"{self.base_url}/cards/{card_id}",
            params=self._get_auth_params({
                "fields": "idBoard,idList"
            })
        )
        response.raise_for_status()
        card = response.json()
        
        # Update card details
        response = requests.put(
            f"{self.base_url}/cards/{card_id}",
            params=self._get_auth_params({
                "name": title,
                "desc": description
            })
        )
        response.raise_for_status()
        
        # Get all lists to find the target list
        lists_response = requests.get(
            f"{self.base_url}/boards/{card['idBoard']}/lists",
            params=self._get_auth_params()
        )
        lists_response.raise_for_status()
        lists = lists_response.json()
        
        # Find the target list and move the card if needed
        target_list = next(l for l in lists if l["name"] == status)
        if card["idList"] != target_list["id"]:
            response = requests.put(
                f"{self.base_url}/cards/{card_id}/idList",
                params=self._get_auth_params({
                    "value": target_list["id"]
                })
            )
            response.raise_for_status()
            
            try:
                # Try to update Power-Up data
                response = requests.put(
                    f"{self.base_url}/cards/{card_id}/pluginData",
                    params=self._get_auth_params({
                        "value": json.dumps({
                            "type": "ai_dev_team_card",
                            "status": status
                        })
                    })
                )
                response.raise_for_status()
            except Exception as e:
                self.logger.warning(f"Failed to update Power-Up data: {str(e)}")
                # Continue even if Power-Up data update fails
                pass