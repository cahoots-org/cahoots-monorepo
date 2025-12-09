"""Configuration for Workspace Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Workspace Service configuration."""

    # Gitea configuration
    gitea_url: str = "http://gitea:3000"
    gitea_api_token: str = ""
    gitea_bot_username: str = "cahoots-bot"

    # GitHub integration (paid feature)
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None

    # Workspace storage
    workspaces_root: str = "/workspaces"

    # Redis for caching
    redis_url: str = "redis://redis:6379"

    # Context Engine
    context_engine_url: str = "http://context-engine:8001"

    # Service authentication
    service_auth_token: str = ""

    # Commit settings
    commit_author_name: str = "Cahoots Bot"
    commit_author_email: str = "bot@cahoots.dev"

    class Config:
        env_file = ".env"
        env_prefix = "WORKSPACE_"


settings = Settings()
