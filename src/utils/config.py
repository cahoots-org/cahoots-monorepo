# src/utils/config.py
"""Configuration management and validation module."""
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator, ConfigDict

class ServiceConfig(BaseModel):
    """Service configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "service1",
                "url": "http://service1.example.com",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1,
                "api_key": "secret-key",
                "api_secret": "secret-token"
            }
        }
    )
    
    name: str
    url: str
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

class APIConfig(BaseModel):
    """API configuration model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "api_keys": ["key1", "key2"],
                "version": "1.0.0"
            }
        }
    )
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    api_keys: List[str] = []
    version: str = "1.0.0"

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
                }
            }
        }
    )
    
    env: str = "development"
    sentinel_nodes: Optional[List[str]] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    services: Dict[str, ServiceConfig] = {}
    api: Optional[APIConfig] = None
    auth: Optional[AuthConfig] = None
    
    @field_validator('sentinel_nodes', mode='before')
    def validate_sentinel_nodes(cls, v):
        """Validate sentinel nodes."""
        if v is None:
            return []
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
    auth=AuthConfig(api_key="test-api-key")
)
