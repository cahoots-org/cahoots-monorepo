"""Core exception classes for standardized error handling."""

import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    INFRASTRUCTURE = "infrastructure"
    EXTERNAL_SERVICE = "external_service"


class BaseError(Exception):
    """Base error class for all application errors."""

    def __init__(
        self,
        message: str,
        code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize base error.

        Args:
            message: Error message
            code: Error code
            category: Error category
            severity: Error severity
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.details = details or {}

        # Log error
        log_level = getattr(logging, severity.upper())
        logger.log(
            log_level,
            self.message,
            extra={
                "error_code": self.code,
                "error_category": self.category,
                "error_details": self.details,
            },
        )

        super().__init__(self.message)


class ServiceError(BaseError):
    """Error raised by service layer."""

    def __init__(
        self,
        service: str,
        operation: str,
        message: str,
        code: str = "SERVICE_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize service error.

        Args:
            service: Service name
            operation: Operation that failed
            message: Error message
            code: Error code
            severity: Error severity
            details: Additional error details
        """
        details = details or {}
        details.update({"service": service, "operation": operation})
        super().__init__(
            message=message,
            code=code,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=severity,
            details=details,
        )


class ValidationError(BaseError):
    """Error raised for validation failures."""

    def __init__(
        self,
        message: str,
        field: str,
        code: str = "VALIDATION_ERROR",
        severity: ErrorSeverity = ErrorSeverity.WARNING,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            code: Error code
            severity: Error severity
            details: Additional error details
        """
        details = details or {}
        details.update({"field": field})
        super().__init__(
            message=message,
            code=code,
            category=ErrorCategory.VALIDATION,
            severity=severity,
            details=details,
        )


class AuthError(BaseError):
    """Error raised for authentication/authorization failures."""

    def __init__(
        self,
        message: str,
        code: str = "AUTH_ERROR",
        category: ErrorCategory = ErrorCategory.AUTHENTICATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize auth error.

        Args:
            message: Error message
            code: Error code
            category: Error category (authentication or authorization)
            severity: Error severity
            details: Additional error details
        """
        super().__init__(
            message=message, code=code, category=category, severity=severity, details=details
        )


class DomainError(BaseError):
    """Error raised for business logic violations."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize domain error.

        Args:
            message: Error message
            code: Error code
            severity: Error severity
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=severity,
            details=details,
        )


class InfrastructureError(BaseError):
    """Error raised for infrastructure failures."""

    def __init__(
        self,
        message: str,
        component: str,
        code: str = "INFRASTRUCTURE_ERROR",
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize infrastructure error.

        Args:
            message: Error message
            component: Failed infrastructure component
            code: Error code
            severity: Error severity
            details: Additional error details
        """
        details = details or {}
        details.update({"component": component})
        super().__init__(
            message=message,
            code=code,
            category=ErrorCategory.INFRASTRUCTURE,
            severity=severity,
            details=details,
        )
