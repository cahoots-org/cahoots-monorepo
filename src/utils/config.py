# src/utils/config.py
"""Configuration management and validation module."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, field_validator, ConfigDict, SecretStr, Field
from src.utils.exceptions import ConfigurationError

class ServiceConfig(BaseModel):
    """Base configuration for services with common fields."""
    
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    api_key: Optional[str] = Field(default=None, description="API key for service authentication")
    
    @field_validator("timeout")
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ConfigurationError("Timeout must be positive")
        return v
        
    @field_validator("retry_attempts")
    def validate_retry_attempts(cls, v: int) -> int:
        """Validate retry attempts is positive."""
        if v < 0:
            raise ConfigurationError("Retry attempts must be non-negative")
        return v
        
    @field_validator("retry_delay") 
    def validate_retry_delay(cls, v: int) -> int:
        """Validate retry delay is positive."""
        if v <= 0:
            raise ConfigurationError("Retry delay must be positive")
        return v
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceConfig":
        """Create config from dictionary with validation."""
        try:
            return cls(**data)
        except Exception as e:
            raise ConfigurationError(f"Invalid service configuration: {str(e)}")
            
    @classmethod
    def from_env(cls, prefix: str, **defaults) -> "ServiceConfig":
        """Create config from environment variables.
        
        Args:
            prefix: Prefix for environment variables (e.g. "TRELLO_")
            **defaults: Default values for fields
            
        Returns:
            ServiceConfig instance
        """
        import os
        
        data = {}
        for field in cls.model_fields:
            env_key = f"{prefix}{field.upper()}"
            if env_key in os.environ:
                data[field] = os.environ[env_key]
            elif field in defaults:
                data[field] = defaults[field]
                
        return cls.from_dict(data)

class StripeConfig(BaseModel):
    """Stripe configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "secret_key": "sk_test_...",
                "webhook_secret": "whsec_..."
            }
        }
    )
    
    secret_key: SecretStr
    webhook_secret: SecretStr

class APIConfig(BaseModel):
    """API configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "api_keys": ["key1", "key2"],
                "version": "1.0.0",
                "cors_origins": ["http://localhost:3000"]
            }
        }
    )
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    api_keys: List[str] = []
    version: str = "1.0.0"
    cors_origins: List[str] = ["http://localhost:3000"]

class AuthConfig(BaseModel):
    """Authentication configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key": "secret-key",
                "jwt_secret": "secret-jwt-key",
                "token_expiry": 3600
            }
        }
    )
    
    api_key: str
    jwt_secret: Optional[str] = None
    token_expiry: int = 3600

class Config(BaseModel):
    """Configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "env": "development",
                "service_name": "ai_dev_team",
                "sentinel_nodes": ["node1", "node2"],
                "redis_host": "localhost",
                "redis_port": 6379,
                "redis_db": 0,
                "services": {
                    "service1": {
                        "name": "service1",
                        "url": "http://service1.example.com",
                        "timeout": 30
                    }
                },
                "api": {
                    "host": "0.0.0.0",
                    "port": 8000
                },
                "auth": {
                    "api_key": "secret-key"
                },
                "stripe": {
                    "secret_key": "sk_test_...",
                    "webhook_secret": "whsec_..."
                }
            }
        }
    )
    
    env: str = "development"
    service_name: str = "ai_dev_team"
    sentinel_nodes: Optional[List[str]] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    services: Dict[str, ServiceConfig] = {}
    api: Optional[APIConfig] = None
    auth: Optional[AuthConfig] = None
    stripe: Optional[StripeConfig] = None
    
    @field_validator('sentinel_nodes', mode='before')
    def validate_sentinel_nodes(cls, v):
        """Validate sentinel nodes."""
        if v is None:
            return []
        return v

class TrelloConfig(ServiceConfig):
    """Trello-specific configuration."""
    
    api_token: Optional[str] = Field(default=None, description="Trello API token")
    organization_id: Optional[str] = Field(default=None, description="Trello organization ID")
    board_template_id: Optional[str] = Field(default=None, description="Template board ID")
    
    @classmethod
    def from_env(cls, **defaults) -> "TrelloConfig":
        """Create Trello config from environment variables."""
        return super().from_env(prefix="TRELLO_", **defaults)
        
    @field_validator("api_key")
    def validate_api_key(cls, v: Optional[str]) -> str:
        """Validate API key is present."""
        if not v:
            raise ConfigurationError("Trello API key is required")
        return v
        
    @field_validator("api_token")
    def validate_api_token(cls, v: Optional[str]) -> str:
        """Validate API token is present."""
        if not v:
            raise ConfigurationError("Trello API token is required")
        return v

# Create and export config instance with default values
config = Config(
    env="development",
    services={
        "together": ServiceConfig(
            name="together",
            url="https://api.together.xyz",
            api_key="test_api_key"
        ),
        "github": ServiceConfig(
            name="github",
            url="https://api.github.com",
            api_key="test-github-key"
        )
    },
    api=APIConfig(),
    auth=AuthConfig(api_key="test-api-key"),
    stripe=StripeConfig(
        secret_key="test-stripe-key",
        webhook_secret="test-stripe-webhook-secret"
    )
)
