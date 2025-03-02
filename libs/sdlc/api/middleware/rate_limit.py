import json
import time
from typing import Optional, Tuple

import redis
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """Rate limiting middleware using Redis"""

    def __init__(
        self,
        redis_url: str,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000,
    ):
        self.redis = redis.from_url(redis_url)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_hour = rate_limit_per_hour
        self.rate_limit_per_day = rate_limit_per_day

    def _get_client_identifier(self, request: Request) -> str:
        """Get a unique identifier for the client"""
        # Try to get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return str(user_id)

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host

    def _get_rate_limit_keys(self, identifier: str) -> Tuple[str, str, str]:
        """Get Redis keys for different time windows"""
        minute_key = f"rate_limit:{identifier}:minute"
        hour_key = f"rate_limit:{identifier}:hour"
        day_key = f"rate_limit:{identifier}:day"
        return minute_key, hour_key, day_key

    def _check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Optional[int]]:
        """Check rate limit for a specific time window"""
        current = int(time.time())
        pipeline = self.redis.pipeline()

        # Remove old entries
        pipeline.zremrangebyscore(key, 0, current - window)
        # Add current request
        pipeline.zadd(key, {str(current): current})
        # Count requests in window
        pipeline.zcard(key)
        # Set expiry
        pipeline.expire(key, window)

        _, _, count, _ = pipeline.execute()

        return count <= limit, limit - count

    async def __call__(self, request: Request, call_next):
        """Rate limiting middleware"""
        identifier = self._get_client_identifier(request)
        minute_key, hour_key, day_key = self._get_rate_limit_keys(identifier)

        # Check rate limits
        minute_ok, minute_remaining = self._check_rate_limit(
            minute_key, self.rate_limit_per_minute, 60
        )
        hour_ok, hour_remaining = self._check_rate_limit(hour_key, self.rate_limit_per_hour, 3600)
        day_ok, day_remaining = self._check_rate_limit(day_key, self.rate_limit_per_day, 86400)

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit-Minute": str(self.rate_limit_per_minute),
            "X-RateLimit-Remaining-Minute": str(minute_remaining),
            "X-RateLimit-Limit-Hour": str(self.rate_limit_per_hour),
            "X-RateLimit-Remaining-Hour": str(hour_remaining),
            "X-RateLimit-Limit-Day": str(self.rate_limit_per_day),
            "X-RateLimit-Remaining-Day": str(day_remaining),
        }

        # Check if any limit is exceeded
        if not all([minute_ok, hour_ok, day_ok]):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limits": {
                        "minute": {
                            "limit": self.rate_limit_per_minute,
                            "remaining": minute_remaining,
                        },
                        "hour": {"limit": self.rate_limit_per_hour, "remaining": hour_remaining},
                        "day": {"limit": self.rate_limit_per_day, "remaining": day_remaining},
                    },
                },
                headers=headers,
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response
