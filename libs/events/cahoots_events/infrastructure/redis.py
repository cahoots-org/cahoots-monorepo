"""Redis client for events package."""
from typing import Optional
from redis.asyncio import Redis, from_url as redis_from_url

async def get_redis_client(
    url: Optional[str] = None,
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> Redis:
    """Get Redis client instance.
    
    Args:
        url: Redis URL. If provided, other connection params are ignored
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        **kwargs: Additional Redis client options
        
    Returns:
        Redis client instance
    """
    if url:
        return redis_from_url(url, **kwargs)
    
    return Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        **kwargs
    ) 