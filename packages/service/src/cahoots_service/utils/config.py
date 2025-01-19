"""Configuration settings for the application."""
from typing import Dict, Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_dev_team",
        description="Database connection URL"
    )
    
    # Redis
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
            "max_agents": 3,
            "max_memory": "2Gi",
            "max_cpu": "1"
        },
        description="Default resource limits for projects"
    )
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False 