"""Trello service configuration."""
from typing import Optional
from cahoots_core.utils.errors.exceptions import ConfigurationError
from pydantic import Field, field_validator, ValidationError
from cahoots_core.utils.config import Config

class TrelloConfig(Config):
    """Trello service configuration."""
    
    name: str = "trello"
    url: str = "https://api.trello.com/1"
    base_url: str = "https://api.trello.com/1"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    webhook_url: Optional[str] = None
    
    # Required fields
    api_key: str = Field(..., description="Trello API key")
    api_token: str = Field(..., description="Trello API token")
    
    # Optional fields
    organization_id: Optional[str] = Field(default=None, description="Trello organization ID")
    board_template_id: Optional[str] = Field(default=None, description="Template board ID")
    
    @classmethod
    def from_env(cls, **defaults) -> "TrelloConfig":
        """Create config from environment variables.
        
        Environment variables:
            TRELLO_API_KEY: Trello API key
            TRELLO_API_TOKEN: Trello API token
            TRELLO_BASE_URL: Base URL for Trello API
            TRELLO_TIMEOUT: Request timeout in seconds
            
        Returns:
            TrelloConfig instance
            
        Raises:
            ConfigurationError: If required environment variables are missing
        """
        try:
            return super().from_env(prefix="TRELLO_", **defaults)
        except ValidationError as e:
            raise ConfigurationError(
                message="Invalid service configuration",
                details={"validation_errors": str(e)}
            )
    
    @field_validator("api_key")
    def validate_api_key(cls, v: Optional[str]) -> str:
        """Validate API key is present."""
        if not v:
            raise ConfigurationError(
                message="Trello API key is required",
                field="api_key"
            )
        return v
        
    @field_validator("api_token")
    def validate_api_token(cls, v: Optional[str]) -> str:
        """Validate API token is present."""
        if not v:
            raise ConfigurationError(
                message="Trello API token is required",
                field="api_token"
            )
        return v
    
    def __init__(self, **data):
        """Initialize TrelloConfig with validation."""
        try:
            super().__init__(**data)
        except ValidationError as e:
            raise ConfigurationError(
                message="Invalid service configuration",
                details={"validation_errors": str(e)}
            )