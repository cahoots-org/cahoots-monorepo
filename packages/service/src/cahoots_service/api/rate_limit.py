"""Rate limiting middleware."""
from typing import Callable, Dict, Optional, Any
from fastapi import Request, Response
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.utils.logger import Logger
from cahoots_core.exceptions import RateLimitError

logger = Logger("Rate-Limit")

class RateLimitMiddleware:
    """Rate limiting middleware."""

    def __init__(
        self,
        app: ASGIApp,
        redis: Any,
        limit: int,
        window: int,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        """Initialize rate limit middleware.
        
        Args:
            app: The ASGI application
            redis: Redis client for rate limiting
            limit: Maximum number of requests per window
            window: Time window in seconds
            key_func: Optional function to generate rate limit key from request
        """
        self.app = app
        self.redis = redis
        self.limit = limit
        self.window = window
        self.key_func = key_func or self._default_key_func

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an incoming request.
        
        Args:
            scope: ASGI connection scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        key = self.key_func(request)

        try:
            # Check rate limit
            count = await self._check_rate_limit(key)
            
            # Add rate limit headers
            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers.update([
                        (b"X-RateLimit-Limit", str(self.limit).encode()),
                        (b"X-RateLimit-Remaining", str(max(0, self.limit - count)).encode()),
                        (b"X-RateLimit-Reset", str(self.window).encode()),
                    ])
                    message["headers"] = [
                        [k, v] for k, v in headers.items()
                    ]
                await send(message)

            await self.app(scope, receive, send_wrapper)

        except RateLimitError as e:
            response = Response(
                content={"detail": str(e)},
                status_code=429,
                headers={
                    "Retry-After": str(e.details["reset"]),
                    "X-RateLimit-Limit": str(e.details["limit"]),
                    "X-RateLimit-Reset": str(e.details["reset"]),
                    "X-RateLimit-Window": str(e.details["window"])
                }
            )
            await response(scope, receive, send)
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            await self.app(scope, receive, send)

    def _default_key_func(self, request: Request) -> str:
        """Generate default rate limit key from request.
        
        Args:
            request: The incoming request
            
        Returns:
            str: Rate limit key
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"rate_limit:{ip}"

    async def _check_rate_limit(self, key: str) -> int:
        """Check if request is within rate limit.
        
        Args:
            key: Rate limit key
            
        Returns:
            int: Current request count
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        try:
            count = await self.redis.incr(key)
            
            if count == 1:
                await self.redis.expire(key, self.window)
            
            if count > self.limit:
                ttl = await self.redis.ttl(key)
                raise RateLimitError(
                    message="Rate limit exceeded",
                    details={
                        "limit": self.limit,
                        "reset": ttl,
                        "window": self.window
                    }
                )
            
            return count
            
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Failed to check rate limit: {str(e)}")
            return 0

def add_rate_limit_headers(
    response: Response,
    limit: int,
    remaining: int,
    reset: int
) -> None:
    """Add rate limit headers to response.
    
    Args:
        response: The response to add headers to
        limit: Rate limit
        remaining: Remaining requests
        reset: Time until reset
    """
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset) 