"""Rate limiting middleware."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException
from src.utils.infrastructure import RedisClient, get_redis_client

class RateLimiter:
    """Rate limiting middleware."""
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        rate_limit: int = 100,
        time_window: int = 60
    ):
        """Initialize rate limiter.
        
        Args:
            redis_client: Redis client for tracking requests
            rate_limit: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.redis = redis_client or get_redis_client()
        self.rate_limit = rate_limit
        self.time_window = time_window
        
    async def check_rate_limit(
        self,
        key: str,
        rate_limit: Optional[int] = None,
        time_window: Optional[int] = None
    ) -> bool:
        """Check if request is within rate limit."""
        limit = rate_limit or self.rate_limit
        window = time_window or self.time_window
        
        # Get current count
        count = await self.redis.get(key) or 0
        
        if count >= limit:
            return False
            
        # Increment count
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        
        return True
        
    async def __call__(self, request: Request):
        """Apply rate limiting to request."""
        # Get client IP
        client_ip = request.client.host
        
        # Get organization ID from auth
        org_id = request.state.organization_id
        
        # Generate keys
        ip_key = f"rate_limit:ip:{client_ip}"
        org_key = f"rate_limit:org:{org_id}"
        
        # Check IP rate limit
        if not await self.check_rate_limit(ip_key):
            raise HTTPException(
                status_code=429,
                detail="Too many requests from this IP"
            )
            
        # Check organization rate limit
        if not await self.check_rate_limit(org_key):
            raise HTTPException(
                status_code=429,
                detail="Organization rate limit exceeded"
            )
            
        return request 