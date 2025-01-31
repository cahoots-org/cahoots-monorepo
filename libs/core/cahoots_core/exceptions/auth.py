"""Authentication and authorization exceptions for the Cahoots system."""
from typing import Optional, Dict, Any

from fastapi import status

from .base import CahootsError, ErrorCategory, ErrorSeverity
from .api import APIError


class AuthError(APIError):
    """Base class for authentication/authorization errors."""
    
    def __init__(
        self,
        message: str,
        *,
        auth_type: str = "bearer",
        **kwargs
    ):
        """Initialize auth error.
        
        Args:
            message: Error message
            auth_type: Authentication type (e.g., 'bearer', 'basic')
            **kwargs: Additional arguments passed to APIError
        """
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            details={"auth_type": auth_type, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class AuthenticationError(AuthError):
    """Authentication failed error."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message,
            code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            severity=ErrorSeverity.WARNING,
            **kwargs
        )


class InvalidTokenError(AuthenticationError):
    """Invalid token error."""
    
    def __init__(
        self,
        message: str = "Invalid or expired token",
        **kwargs
    ):
        super().__init__(
            message,
            code="INVALID_TOKEN",
            details={"token_valid": False, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class AuthorizationError(AuthError):
    """Authorization failed error."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permissions: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.AUTHORIZATION,
            details={"required_permissions": required_permissions, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class RoleError(AuthorizationError):
    """Role-based authorization error."""
    
    def __init__(
        self,
        message: str = "Invalid role",
        required_roles: Optional[list[str]] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="INVALID_ROLE",
            details={"required_roles": required_roles, **(kwargs.pop("details", {}) or {})},
            **kwargs
        ) 