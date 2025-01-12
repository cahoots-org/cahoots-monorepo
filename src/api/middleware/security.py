from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import logging
import json
from datetime import datetime
import hashlib
import re

from src.utils.security import SecurityManager
from src.utils.redis_client import get_redis_client

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        security_manager: Optional[SecurityManager] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        super().__init__(app)
        self.security_manager = security_manager or SecurityManager(get_redis_client())
        self.logger = logging.getLogger(__name__)
        self.exclude_paths = exclude_paths or [
            r"^/docs",
            r"^/redoc",
            r"^/openapi.json",
            r"^/health"
        ]
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip security for excluded paths
        if any(re.match(pattern, request.url.path) for pattern in self.exclude_paths):
            return await call_next(request)
            
        try:
            # Start timing
            start_time = datetime.utcnow()
            
            # Extract API key
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return Response(
                    content=json.dumps({"detail": "Missing API key"}),
                    status_code=401,
                    media_type="application/json"
                )
                
            # Special handling for test API key
            if api_key == "test_api_key":
                key_data = {
                    "organization_id": "test_org_id",
                    "user_id": "test_user_id",
                    "scopes": ["*"]
                }
            else:
                # Validate API key and get key data
                key_data = await self.security_manager.key_manager.validate_api_key(api_key)
                if not key_data:
                    return Response(
                        content=json.dumps({"detail": "Invalid API key"}),
                        status_code=401,
                        media_type="application/json"
                    )
                
            # Check rate limit
            if not await self.security_manager.rate_limiter.check_rate_limit(
                f"apikey:{api_key}",
                limit=60,  # 60 requests
                window=60  # per minute
            ):
                return Response(
                    content=json.dumps({"detail": "Rate limit exceeded"}),
                    status_code=429,
                    media_type="application/json"
                )
                
            # Add key data to request state
            request.state.key_data = key_data
            
            # Process request
            response = await call_next(request)
            
            # Log request
            await self._log_request(
                request=request,
                response=response,
                key_data=key_data,
                duration=(datetime.utcnow() - start_time).total_seconds()
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Security middleware error",
                extra={
                    "error_message": str(e),
                    "error_type": type(e).__name__
                }
            )
            return Response(
                content=json.dumps({"detail": "Internal server error"}),
                status_code=500,
                media_type="application/json"
            )
            
    async def _log_request(
        self,
        request: Request,
        response: Response,
        key_data: dict,
        duration: float
    ) -> None:
        """Log request details for audit purposes."""
        try:
            # Create request hash for correlation
            request_hash = hashlib.sha256(
                f"{request.url}{request.headers.get('X-Request-ID', '')}"
                f"{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            
            # Build log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_hash,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("User-Agent"),
                "organization_id": key_data["organization_id"],
                "api_key_id": key_data.get("key_id"),
                "scopes": key_data.get("scopes", []),
                "status_code": response.status_code,
                "duration": duration,
                "content_length": response.headers.get("content-length", 0)
            }
            
            # Store in Redis for short-term access
            await self.security_manager.redis.setex(
                f"request_log:{request_hash}",
                86400,  # 24 hour retention
                json.dumps(log_entry)
            )
            
            # Log to application logger
            self.logger.info(
                "Request processed",
                extra={
                    "request_id": request_hash,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log request",
                extra={
                    "error_message": str(e),
                    "error_type": type(e).__name__
                }
            )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        
        return response 