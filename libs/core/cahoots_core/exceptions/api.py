"""API-specific exceptions for the Cahoots system."""
from typing import Any, Dict, Optional

from fastapi import status

from .base import CahootsError, ErrorCategory, ErrorSeverity


class APIError(CahootsError):
    """Base class for API-related errors."""
    
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        **kwargs
    ):
        """Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            **kwargs: Additional arguments passed to CahootsError
        """
        super().__init__(
            message,
            category=ErrorCategory.API,
            details={"status_code": status_code, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )
        self.status_code = status_code


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            severity=ErrorSeverity.WARNING,
            **kwargs
        )


class ValidationError(APIError):
    """Request validation error."""
    
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            severity=ErrorSeverity.WARNING,
            details={"validation_errors": errors, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class ConflictError(APIError):
    """Resource conflict error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            severity=ErrorSeverity.WARNING,
            **kwargs
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            severity=ErrorSeverity.WARNING,
            details={"retry_after": retry_after, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class ServerError(APIError):
    """Internal server error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="INTERNAL_SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs
        )


class ServiceError(APIError):
    """Service-specific error."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            severity=ErrorSeverity.ERROR,
            details={
                "service": service_name,
                "operation": operation,
                **(kwargs.pop("details", {}) or {})
            },
            **kwargs
        ) 