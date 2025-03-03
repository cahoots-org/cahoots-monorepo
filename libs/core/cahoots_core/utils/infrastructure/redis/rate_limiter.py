"""Rate limiter implementation using Redis."""

from datetime import datetime
from typing import Optional

from redis.asyncio import Redis

from cahoots_core.utils.infrastructure.redis.client import get_redis_client


class RateLimiter:
    """Rate limiter using Redis sliding window."""

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize rate limiter.

        Args:
            redis_client: Optional Redis client, will create one if not provided
        """
        self.redis = redis_client or get_redis_client()

    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit.

        Args:
            key: Unique key for the rate limit (e.g. "ip:123.45.67.89")
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds

        # Remove old requests outside window
        await self.redis.zremrangebyscore(key, "-inf", window_start)

        # Count requests in current window
        count = await self.redis.zcard(key)

        if count >= max_requests:
            return False

        # Add current request
        await self.redis.zadd(key, {str(now): now})

        # Set expiry on key
        await self.redis.expire(key, window_seconds)

        return True

    async def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests allowed under rate limit.

        Args:
            key: Unique key for the rate limit
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Number of remaining requests allowed
        """
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds

        # Remove old requests
        await self.redis.zremrangebyscore(key, "-inf", window_start)

        # Count current requests
        count = await self.redis.zcard(key)

        return max(0, max_requests - count)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Key to reset
        """
        await self.redis.delete(key)
