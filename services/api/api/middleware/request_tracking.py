"""Request tracking middleware."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request tracking headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add tracking headers.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response with tracking headers added
        """
        # Generate request ID if not provided
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Call next middleware/route handler
        response = await call_next(request)

        # Add request ID to response headers
        response.headers.append("X-Request-ID", request_id)

        return response


async def add_request_id(request: Request, call_next: Callable) -> Response:
    """Add request ID to request/response cycle.

    This is a convenience function that wraps the RequestTrackingMiddleware
    functionality for use as a middleware function.

    Args:
        request: The incoming request
        call_next: The next middleware/route handler

    Returns:
        Response with request ID header added
    """
    middleware = RequestTrackingMiddleware(app=None)
    return await middleware.dispatch(request, call_next)
