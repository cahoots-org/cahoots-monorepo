"""Project context management."""
from typing import Optional
from contextlib import asynccontextmanager
from src.utils.infrastructure import (
    DatabaseClient,
    RedisClient,
    EventClient,
    KubernetesClient,
    get_db_client,
    get_redis_client,
    get_event_client,
    get_k8s_client
)

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
        self._event_client: Optional[EventClient] = None
        self._k8s_client: Optional[KubernetesClient] = None

    async def init(self):
        """Initialize all clients with project context."""
        # Get project details including shard info
        self._db_client = get_db_client()
        project = await self._db_client.get_project(self.project_id)
        
        # Initialize sharded database client
        self._db_client = get_db_client(
            schema=f"project_{self.project_id}",
            shard=project.database_shard
        )
        
        # Initialize namespaced Redis client
        self._redis_client = get_redis_client(
            namespace=f"project:{self.project_id}"
        )
        
        # Initialize namespaced event client
        self._event_client = get_event_client(
            namespace=f"project:{self.project_id}"
        )
        
        # Initialize Kubernetes client with project namespace
        self._k8s_client = get_k8s_client(
            namespace=f"project-{self.project_id}"
        )

    async def cleanup(self):
        """Cleanup all project resources."""
        if self._db_client:
            await self._db_client.close()
        if self._redis_client:
            await self._redis_client.close()
        if self._event_client:
            await self._event_client.close()

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

    @property
    def events(self) -> EventClient:
        """Get event client."""
        if not self._event_client:
            raise RuntimeError("Event client not initialized")
        return self._event_client

    @property
    def k8s(self) -> KubernetesClient:
        """Get Kubernetes client."""
        if not self._k8s_client:
            raise RuntimeError("Kubernetes client not initialized")
        return self._k8s_client

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