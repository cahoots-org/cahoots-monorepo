"""Security middleware for FastAPI."""

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from utils.security import SecurityManager


class SecurityMiddleware:
    """Security middleware for FastAPI."""

    def __init__(self, app: Callable, security_manager: Optional[SecurityManager] = None):
        """Initialize security middleware.

        Args:
            app: FastAPI application
            security_manager: Security manager instance
        """
        self.app = app
        self.security_manager = security_manager
        self.logger = logging.getLogger(__name__)

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """Process request through security checks.

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip security for health check
        if request.url.path == "/health":
            await self.app(scope, receive, send)
            return

        # Get API key from headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            response = JSONResponse(status_code=401, content={"detail": "Missing API key"})
            await response(scope, receive, send)
            return

        try:
            # Get security manager from state if not set
            if not self.security_manager:
                self.security_manager = request.app.state.security_manager
                if not self.security_manager:
                    response = JSONResponse(
                        status_code=401, content={"detail": "Authentication service unavailable"}
                    )
                    await response(scope, receive, send)
                    return

            # Authenticate request
            key_data = await self.security_manager.authenticate(api_key)
            request.state.key_data = key_data
            await self.app(scope, receive, send)
            return

        except ValueError as e:
            self.logger.warning("Authentication failed: %s", str(e))
            response = JSONResponse(status_code=401, content={"detail": str(e)})
            await response(scope, receive, send)
            return
        except Exception as e:
            self.logger.error("Unexpected error in middleware: %s", str(e))
            response = JSONResponse(status_code=401, content={"detail": "Invalid API key"})
            await response(scope, receive, send)
            return
