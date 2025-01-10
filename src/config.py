"""Application configuration."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_dev_team"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    
    # Authentication
    auth_secret_key: str = "dev-jwt-secret-key-123"
    auth_api_key: str = "dev-api-key-123"
    auth_token_expire_minutes: int = 30
    
    # Stripe
    stripe_api_key: str = "sk_test_..."
    stripe_webhook_secret: str = "whsec_..."
    stripe_secret_key: Optional[str] = None
    
    # GitHub
    github_api_key: Optional[str] = None
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    
    # Together
    together_api_key: Optional[str] = None
    
    # Trello
    trello_api_key: Optional[str] = None
    trello_token: Optional[str] = None
    trello_api_secret: Optional[str] = None
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: int = 100
    
    # Service configuration
    service_name: str = "ai_dev_team"
    environment: str = "development"
    log_level: str = "INFO"
    
    # API configuration
    api_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    # CORS configuration
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # Security configuration
    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"  # Allow extra fields from environment variables
    )

@lru_cache
def get_settings() -> Settings:
    """Get application settings.
    
    Returns:
        Application settings
    """
    return Settings() 