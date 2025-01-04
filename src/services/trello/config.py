"""Trello configuration management."""
from dataclasses import dataclass
from src.utils.config import config

@dataclass
class TrelloConfig:
    """Configuration for Trello service."""
    api_key: str
    api_token: str
    base_url: str = "https://api.trello.com/1"
    timeout: int = 30
    
    @classmethod
    def from_config(cls) -> "TrelloConfig":
        """Create TrelloConfig from global config.
        
        Returns:
            TrelloConfig instance
            
        Raises:
            RuntimeError: If Trello configuration is missing
        """
        if "trello" not in config.services:
            raise RuntimeError(
                "Trello configuration missing. Ensure TRELLO_API_KEY and "
                "TRELLO_API_SECRET environment variables are set."
            )
            
        trello_config = config.services["trello"]
        return cls(
            api_key=trello_config.api_key,
            api_token=trello_config.api_secret,
            base_url=trello_config.url,
            timeout=trello_config.timeout
        ) 