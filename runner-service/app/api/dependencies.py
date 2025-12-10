"""Dependency injection for Runner Service."""

from functools import lru_cache

import redis.asyncio as redis

from app.config import settings
from app.services.cloud_run import CloudRunJobExecutor
from app.services.run_manager import RunManager


@lru_cache()
def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return redis.from_url(settings.redis_url)


@lru_cache()
def get_executor() -> CloudRunJobExecutor:
    """Get Cloud Run executor instance."""
    return CloudRunJobExecutor(
        project_id=settings.gcp_project_id or "",
        region=settings.gcp_region
    )


def get_run_manager() -> RunManager:
    """Get Run Manager instance."""
    return RunManager(
        redis_client=get_redis_client(),
        executor=get_executor()
    )
