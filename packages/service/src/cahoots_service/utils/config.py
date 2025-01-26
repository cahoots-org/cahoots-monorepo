"""Configuration settings for the application."""
from typing import Dict, Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ServiceConfig(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Server settings
    debug: bool = Field(default=True, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Auth settings
    auth_secret_key: str = Field(default="dev-jwt-secret-key-123", description="Auth secret key")
    auth_api_key: str = Field(default="dev-api-key-123", description="Auth API key")
    auth_token_expire_minutes: int = Field(default=30, description="Auth token expiration in minutes")
    
    # Database settings
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Maximum database connection overflow")
    
    # Redis settings
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")
    
    # API keys
    stripe_secret_key: str = Field(default="", description="Stripe secret key")
    github_api_key: str = Field(default="", description="GitHub API key")
    together_api_key: str = Field(default="", description="Together API key")
    trello_api_key: str = Field(default="", description="Trello API key")
    trello_api_secret: str = Field(default="", description="Trello API secret")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_default: int = Field(default=100, description="Default rate limit per minute")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["*"],
        description="List of allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed HTTP headers"
    )
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_dev_team",
        description="Database connection URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Kubernetes
    k8s_config_path: Optional[str] = Field(
        default=None,
        description="Path to Kubernetes config file. If None, uses in-cluster config."
    )
    k8s_namespace: str = Field(
        default="cahoots",
        description="Default Kubernetes namespace"
    )
    
    # Stripe
    stripe_api_key: str = Field(
        default="",
        description="Stripe API key"
    )
    stripe_webhook_secret: str = Field(
        default="",
        description="Stripe webhook secret"
    )
    
    # GitHub
    github_app_id: str = Field(
        default="",
        description="GitHub App ID"
    )
    github_private_key: str = Field(
        default="",
        description="GitHub App private key"
    )
    github_webhook_secret: str = Field(
        default="",
        description="GitHub webhook secret"
    )
    
    # JWT
    jwt_secret_key: str = Field(
        default="secret",
        description="Secret key for JWT tokens"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT tokens"
    )
    jwt_expiration: int = Field(
        default=3600,
        description="JWT token expiration in seconds"
    )
    
    # Service
    service_name: str = Field(
        default="cahoots-service",
        description="Service name"
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Resource limits
    default_resource_limits: Dict = Field(
        default={
            "cpu": "100m",
            "memory": "128Mi"
        },
        description="Default resource limits"
    )

_settings = None

def get_settings() -> ServiceConfig:
    """Get the application settings.

    Returns:
        ServiceConfig: The application settings.
    """
    global _settings
    if _settings is None:
        _settings = ServiceConfig()
    return _settings 