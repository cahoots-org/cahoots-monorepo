"""Redis client utility."""
from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from fastapi import Depends
from src.utils.config import get_settings

_pool: Optional[ConnectionPool] = None

async def get_redis_client(settings=Depends(get_settings)) -> Redis:
    """Get Redis client instance.
    
    Args:
        settings: Application settings
        
    Returns:
        Redis client instance
    """
    global _pool
    
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True
        )
    
    return Redis(connection_pool=_pool)