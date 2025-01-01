# src/utils/config.py
"""Configuration management and validation module."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, SecretStr, model_validator, validator
import yaml
import os
from pathlib import Path
from functools import lru_cache
from .base_logger import BaseLogger

logger = BaseLogger("Config")

class RedisConfig(BaseModel):
    """Redis configuration settings."""
    host: str = Field(..., description="Redis host")
    port: int = Field(..., description="Redis port")
    db: int = Field(0, description="Redis database number")
    password: Optional[SecretStr] = Field(None, description="Redis password")
    cluster_mode: bool = Field(False, description="Whether to use Redis cluster mode")
    sentinel_nodes: Optional[List[str]] = Field(None, description="Redis sentinel nodes")
    sentinel_master: Optional[str] = Field(None, description="Redis sentinel master name")
    socket_timeout: int = Field(5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(2, description="Socket connect timeout in seconds")
    max_connections_per_worker: int = Field(10, description="Maximum connections per worker")
    worker_concurrency: int = Field(4, description="Number of worker processes")
    health_check_interval: int = Field(30, description="Health check interval in seconds")
    client_name: str = "ai_dev_team"

    @validator('sentinel_nodes', always=True)
    def validate_sentinel_nodes(cls, v, values):
        """Validate sentinel configuration."""
        if v and not values.get('sentinel_master'):
            raise ValueError("sentinel_master must be set when using sentinel nodes")
        return v

class AuthConfig(BaseModel):
    """Authentication configuration settings."""
    token_expire_minutes: int = Field(30, description="JWT token expiration time in minutes")
    hash_algorithm: str = Field("HS256", description="Hash algorithm for JWT")
    min_password_length: int = Field(8, description="Minimum password length")
    password_reset_expire_minutes: int = Field(15, description="Password reset token expiration time")
    secret_key: SecretStr = Field(..., description="Secret key for JWT encoding")
    api_key: str = Field(..., description="API key for service authentication")

    @model_validator(mode='before')
    def set_default_secret_key(cls, values):
        """Set a default secret key for development/testing environments."""
        if not values.get('secret_key'):
            env = os.getenv('ENV', 'development')
            if env in ('development', 'test'):
                values['secret_key'] = "default-development-secret-key-change-in-production"
            else:
                raise ValueError("JWT secret key must be provided in production environment")
        return values

class APIConfig(BaseModel):
    """API configuration settings."""
    max_request_size_mb: int = Field(10, description="Maximum request size in MB")
    request_timeout_seconds: int = Field(30, description="Request timeout in seconds")
    rate_limit: Dict[str, int] = Field(
        default_factory=lambda: {"requests_per_minute": 60, "burst_size": 10},
        description="Rate limiting configuration"
    )
    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"], description="Allowed hosts for CORS")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], description="Allowed CORS origins")
    version: str = "0.1.0"

class ServiceConfig(BaseModel):
    """Service configuration settings."""
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service URL")
    timeout: int = Field(30, description="Service timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay: int = Field(1, description="Delay between retries in seconds")
    api_key: Optional[str] = Field(None, description="API key for the service")
    api_secret: Optional[str] = Field(None, description="API secret for the service")

@lru_cache()
def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file and environment variables."""
    # Default config path
    config_path = os.getenv("CONFIG_PATH", "config/default.yaml")
    
    # Load from YAML file
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    else:
        logger.warning(f"Config file not found at {config_path}, using default values")
        config_data = {}
    
    # Override with environment variables
    env_mapping = {
        "ENV": "env",
        "DEBUG": "debug",
        "LOG_LEVEL": "log_level",
        "REDIS_HOST": "redis.host",
        "REDIS_PORT": "redis.port",
        "REDIS_PASSWORD": "redis.password",
        "AUTH_SECRET_KEY": "auth.secret_key",
        "AUTH_API_KEY": "auth.api_key",
        "GITHUB_API_KEY": "services.github.api_key",
        "TRELLO_API_KEY": "services.trello.api_key",
        "TRELLO_API_SECRET": "services.trello.api_secret"
    }
    
    for env_var, config_path in env_mapping.items():
        if env_value := os.getenv(env_var):
            # Split the path and set nested value
            parts = config_path.split(".")
            current = config_data
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = env_value
    
    return config_data

class Config(BaseModel):
    """Main configuration settings."""
    env: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    redis: RedisConfig = Field(default_factory=lambda: RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        client_name="ai_dev_team"
    ))
    auth: AuthConfig = Field(default_factory=lambda: AuthConfig(
        token_expire_minutes=30,
        hash_algorithm="HS256",
        min_password_length=8,
        password_reset_expire_minutes=15,
        secret_key="development-secret-key",
        api_key="test-api-key-123"
    ))
    api: APIConfig = Field(default_factory=lambda: APIConfig(
        max_request_size_mb=10,
        request_timeout_seconds=30,
        rate_limit={"requests_per_minute": 60, "burst_size": 10},
        allowed_hosts=["*"],
        cors_origins=["*"],
        version="0.1.0"
    ))
    services: Dict[str, ServiceConfig] = Field(default_factory=lambda: {
        "github": ServiceConfig(
            name="github",
            url="https://api.github.com",
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            api_key=os.getenv("GITHUB_API_KEY", "test-github-key")
        ),
        "trello": ServiceConfig(
            name="trello",
            url="https://api.trello.com/1",
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            api_key=os.getenv("TRELLO_API_KEY"),
            api_secret=os.getenv("TRELLO_API_SECRET")
        )
    })
    
    def __init__(self, **kwargs):
        """Initialize configuration with values from YAML and environment."""
        config_data = load_config()
        # Merge config_data with kwargs, with kwargs taking precedence
        merged_data = {**config_data, **kwargs}
        super().__init__(**merged_data)
    
    @property
    def github_api_key(self) -> Optional[str]:
        """Get GitHub API key."""
        return self.services.get("github", {}).api_key
    
    @property
    def trello_api_key(self) -> Optional[str]:
        """Get Trello API key."""
        return self.services.get("trello", {}).api_key
    
    @property
    def trello_api_secret(self) -> Optional[str]:
        """Get Trello API secret."""
        return self.services.get("trello", {}).api_secret
    
    @model_validator(mode='after')
    def validate_environment(cls, values):
        """Validate environment-specific settings."""
        env = values.env
        if env == 'production':
            if values.debug:
                raise ValueError("Debug mode cannot be enabled in production")
            if values.log_level == 'DEBUG':
                raise ValueError("Debug log level cannot be used in production")
        return values

# Create global config instance
config = Config()

# Export config instance
__all__ = ['config', 'Config', 'RedisConfig', 'AuthConfig', 'APIConfig', 'ServiceConfig']
