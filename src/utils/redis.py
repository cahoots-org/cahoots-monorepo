"""Redis client utilities."""
from redis.asyncio import Redis, ConnectionPool
from functools import lru_cache

from src.utils.config import get_settings

@lru_cache()
def get_redis_pool() -> ConnectionPool:
    """Get Redis connection pool.
    
    Returns:
        Redis connection pool
    """
    settings = get_settings()
    return ConnectionPool.from_url(str(settings.REDIS_URL))

async def get_redis_client() -> Redis:
    """Get Redis client.
    
    Returns:
        Redis client
    """
    pool = get_redis_pool()
    return Redis(connection_pool=pool) 