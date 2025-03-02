"""Project context management."""

from contextlib import asynccontextmanager
from typing import Optional

from cahoots_core.utils.infrastructure.database.client import (
    DatabaseClient,
    get_db_client,
)
from cahoots_core.utils.infrastructure.redis.client import RedisClient, get_redis_client


class ProjectContext:
    """Context manager for project-specific resources."""

    def __init__(self, project_id: str):
        """Initialize project context.

        Args:
            project_id: The project ID to scope resources to
        """
        self.project_id = project_id
        self._db_client: Optional[DatabaseClient] = None
        self._redis_client: Optional[RedisClient] = None

    async def init(self):
        """Initialize all clients with project context."""
        # Get project details including shard info
        self._db_client = get_db_client()
        project = await self._db_client.get_project(self.project_id)

        # Initialize sharded database client
        self._db_client = get_db_client(
            schema=f"project_{self.project_id}", shard=project.database_shard
        )

        # Initialize namespaced Redis client
        self._redis_client = get_redis_client(namespace=f"project:{self.project_id}")

    async def cleanup(self):
        """Cleanup all project resources."""
        if self._db_client:
            await self._db_client.close()
        if self._redis_client:
            await self._redis_client.close()

    @property
    def db(self) -> DatabaseClient:
        """Get database client."""
        if not self._db_client:
            raise RuntimeError("Database client not initialized")
        return self._db_client

    @property
    def redis(self) -> RedisClient:
        """Get Redis client."""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized")
        return self._redis_client


@asynccontextmanager
async def project_context(project_id: str):
    """Async context manager for project resources.

    Usage:
        async with project_context("project-123") as ctx:
            await ctx.db.query(...)
            await ctx.redis.get(...)
            await ctx.events.publish(...)
    """
    ctx = ProjectContext(project_id)
    try:
        await ctx.init()
        yield ctx
    finally:
        await ctx.cleanup()
