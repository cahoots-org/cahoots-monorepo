"""Dependency injection for Workspace Service."""

from functools import lru_cache
from typing import Optional

from app.clients.gitea import GiteaClient
from app.clients.context_engine import ContextEngineClient
from app.services.workspace import WorkspaceService
from app.config import settings


@lru_cache()
def get_gitea_client() -> GiteaClient:
    """Get Gitea client instance."""
    return GiteaClient(
        base_url=settings.gitea_url,
        api_token=settings.gitea_api_token,
        bot_username=settings.gitea_bot_username
    )


@lru_cache()
def get_context_engine_client() -> Optional[ContextEngineClient]:
    """Get Context Engine client instance."""
    if not settings.context_engine_url:
        return None
    return ContextEngineClient(
        base_url=settings.context_engine_url
    )


def get_workspace_service() -> WorkspaceService:
    """Get Workspace Service instance."""
    return WorkspaceService(
        gitea_client=get_gitea_client(),
        context_engine_client=get_context_engine_client()
    )
