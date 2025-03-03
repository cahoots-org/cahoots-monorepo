"""Caching utilities."""

import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from redis.asyncio import Redis

from cahoots_core.utils.infrastructure.redis.client import get_redis_client

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """Manager for caching operations."""

    def __init__(self, redis: Optional[Redis] = None, prefix: str = "cache", ttl: int = 3600):
        """Initialize cache manager."""
        self.redis = redis
        self.prefix = prefix
        self.ttl = ttl

    async def get_redis(self) -> Redis:
        """Get Redis client."""
        if self.redis is None:
            self.redis = await get_redis_client()
        return self.redis

    def make_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key."""
        return cache_key(self.prefix, *args, **kwargs)

    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        redis = await self.get_redis()
        return await get_cached(key, redis)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        redis = await self.get_redis()
        return await set_cached(key, value, ttl or self.ttl, redis)

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        redis = await self.get_redis()
        try:
            await redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Error deleting cache key {key}: {e}")
            return False

    async def clear_prefix(self, prefix: Optional[str] = None) -> bool:
        """Clear all keys with given prefix."""
        redis = await self.get_redis()
        try:
            pattern = f"{prefix or self.prefix}:*"
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Error clearing cache prefix {prefix}: {e}")
            return False


def cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a cache key from prefix and arguments."""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


async def get_cached(key: str, redis: Optional[Redis] = None) -> Optional[str]:
    """Get a value from cache."""
    if redis is None:
        redis = await get_redis_client()
    try:
        return await redis.get(key)
    except Exception as e:
        logger.warning(f"Error getting cache key {key}: {e}")
        return None


async def set_cached(key: str, value: Any, ttl: int = 3600, redis: Optional[Redis] = None) -> bool:
    """Set a value in cache with TTL."""
    if redis is None:
        redis = await get_redis_client()
    try:
        await redis.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Error setting cache key {key}: {e}")
        return False


def cached(prefix: str, ttl: int = 3600) -> Callable:
    """Cache decorator for async functions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = cache_key(prefix, *args, **kwargs)
            redis = await get_redis_client()

            # Try to get from cache
            cached_value = await get_cached(key, redis)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    return cached_value

            # Get fresh value
            value = await func(*args, **kwargs)

            # Cache the value
            await set_cached(key, value, ttl, redis)

            return value

        return wrapper

    return decorator
