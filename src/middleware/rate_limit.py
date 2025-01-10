"""Rate limiting middleware."""
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import json

from src.models.organization import Organization
from src.models.api_key import APIKey
from src.utils.security import hash_api_key
from src.utils.redis_client import get_redis_client

class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self, db: AsyncSession):
        """Initialize rate limiter.
        
        Args:
            db: Database session
        """
        self.db = db
        self.redis = get_redis_client()
        self.default_limit = 60  # requests per minute
        self.default_window = 60  # seconds
        
    async def get_organization_limits(self, api_key: str) -> Dict[str, int]:
        """Get rate limits for organization.
        
        Args:
            api_key: API key
            
        Returns:
            Dict[str, int]: Rate limit configuration
            
        Raises:
            HTTPException: If organization not found
        """
        # Look up API key
        stmt = select(APIKey).join(
            Organization,
            APIKey.organization_id == Organization.id
        ).where(
            APIKey.hashed_key == hash_api_key(api_key),
            APIKey.is_active == True
        )
        result = await self.db.execute(stmt)
        key_with_org = result.scalar_one_or_none()
        
        if not key_with_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
            
        # Get organization's rate limits
        org = key_with_org.organization
        subscription = org.subscription
        
        if not subscription or subscription.is_expired():
            return {
                "limit": self.default_limit,
                "window": self.default_window
            }
            
        return {
            "limit": subscription.rate_limit or self.default_limit,
            "window": subscription.rate_limit_window or self.default_window
        }
        
    async def is_rate_limited(self, request: Request) -> bool:
        """Check if request should be rate limited.
        
        Args:
            request: FastAPI request
            
        Returns:
            bool: True if request should be rate limited
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return False
            
        try:
            # Get organization's rate limits
            limits = await self.get_organization_limits(api_key)
            
            # Check rate limit
            key = f"ratelimit:{hash_api_key(api_key)}"
            window_start = int(datetime.utcnow().timestamp() / limits["window"]) * limits["window"]
            
            # Get current count
            count = await self.redis.get(key)
            count = int(count) if count else 0
            
            if count >= limits["limit"]:
                # Get time until reset
                window_end = window_start + limits["window"]
                reset_in = window_end - datetime.utcnow().timestamp()
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "reset_in": int(reset_in),
                        "limit": limits["limit"],
                        "window": limits["window"]
                    }
                )
                
            # Increment counter
            pipeline = self.redis.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, limits["window"])
            await pipeline.execute()
            
            # Add rate limit headers
            remaining = limits["limit"] - (count + 1)
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit = limits["limit"]
            request.state.rate_limit_reset = window_start + limits["window"]
            
            return False
            
        except HTTPException:
            raise
        except Exception as e:
            # Log error but don't rate limit on errors
            print(f"Rate limit error: {str(e)}")
            return False 