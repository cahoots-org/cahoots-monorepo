"""Configuration utilities."""
from typing import Dict, Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class ServiceConfig(BaseSettings):
    """Service configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Server settings
    debug: bool = Field(default=True, description="Debug mode")
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    public_url: str = Field(default="http://localhost:3000", description="Public URL for the application")
    
    # Auth settings
    jwt_secret_key: str = Field(default="your-secret-key", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration: int = Field(default=30, description="JWT expiration in minutes")
    auth_token_expire_minutes: int = Field(default=30, description="Auth token expiration in minutes")
    
    # OAuth settings
    google_client_id: str = Field(default="", description="Google OAuth client ID")
    google_client_secret: str = Field(default="", description="Google OAuth client secret")
    github_client_id: str = Field(default="", description="GitHub OAuth client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth client secret")
    
    # Database settings
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/cahoots", description="Database URL")
    sql_echo: bool = Field(default=False, description="Enable SQL echo")
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Maximum database connection overflow")
    
    # Redis settings
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis URL")
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

class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Redis settings
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis URL")
    secret_key: str = Field(default="your-secret-key", description="Secret key")
    access_token_expire_minutes: int = Field(default=15, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration in days")

_settings = None

@lru_cache()
def get_settings() -> ServiceConfig:
    """Get the application settings.

    Returns:
        ServiceConfig: The application settings.
    """
    global _settings
    if _settings is None:
        _settings = ServiceConfig()
    return _settings

@lru_cache()
def get_security_config() -> SecurityConfig:
    """Get security configuration.
    
    Returns:
        Security configuration
    """
    settings = get_settings()
    return SecurityConfig(
        redis_url=settings.redis_url,
        secret_key=settings.jwt_secret_key,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days
    ) 