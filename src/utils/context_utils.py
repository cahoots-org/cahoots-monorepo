from typing import Dict
import redis.asyncio as redis

class ContextClient:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get_role_context(
        self,
        project_id: str,
        role: str,
        limit_mb: int
    ) -> Dict:
        """Get context for a specific role."""
        context_key = f"context:{project_id}:{role}"
        context = await self.redis.get(context_key)
        return context or {}

    async def set_role_context_limit(
        self,
        project_id: str,
        role: str,
        limit_mb: int
    ):
        """Set context limit for a role."""
        limit_key = f"context_limit:{project_id}:{role}"
        await self.redis.set(limit_key, str(limit_mb)) 