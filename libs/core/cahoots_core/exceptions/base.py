"""Base exception classes for the Cahoots system."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Categories of errors."""

    VALIDATION = "validation"
    INFRASTRUCTURE = "infrastructure"
    BUSINESS = "business"
    SECURITY = "security"
    SYSTEM = "system"
    API = "api"
    UNKNOWN = "unknown"
    RESOURCE_LIMIT = "resource_limit"


class ErrorContext:
    """Context information for errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.message = message
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class CahootsError(Exception):
    """Base error class for all Cahoots errors."""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **kwargs,
    ):
        """Initialize error.

        Args:
            message: Error message
            category: Error category
            details: Additional error details
            severity: Error severity
            **kwargs: Additional arguments
        """
        super().__init__(message)
        self.message = message
        self._category = category
        self._details = details or {}
        self._severity = severity

        # Handle code argument if provided
        if "code" in kwargs:
            self._details["code"] = kwargs.pop("code")

        # Add any remaining kwargs to details
        self._details.update(kwargs)

    @property
    def severity(self) -> ErrorSeverity:
        """Get the error severity."""
        return self._severity

    @severity.setter
    def severity(self, value: ErrorSeverity) -> None:
        """Set the error severity."""
        self._severity = value

    @property
    def category(self) -> ErrorCategory:
        """Get the error category."""
        return self._category

    @category.setter
    def category(self, value: ErrorCategory) -> None:
        """Set the error category."""
        self._category = value

    @property
    def details(self) -> Dict[str, Any]:
        """Get the error details."""
        return self._details

    @details.setter
    def details(self, value: Dict[str, Any]) -> None:
        """Set the error details."""
        self._details = value

    @property
    def context(self) -> ErrorContext:
        """Get the error context."""
        return ErrorContext(
            message=self.message,
            severity=self.severity,
            category=self.category,
            details=self.details,
            timestamp=datetime.utcnow(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        error_dict = self.context.to_dict()
        return error_dict

    def __str__(self) -> str:
        """Get string representation."""
        return f"{type(self).__name__}: {self.message}"


class AIDTException(CahootsError):
    """Base exception for AI Development Team errors.

    This is a specialized version of CahootsError for the AI Development Team
    subsystem. It provides the same functionality but with a distinct type
    for more specific error handling.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "AIDT_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize the error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code for categorization
            severity: Error severity level
            category: Error category for classification
            details: Additional error details/context
            cause: Original exception that caused this error
        """
        super().__init__(
            message, severity=severity, category=category, details=details, cause=cause
        )


class ContextLimitError(CahootsError):
    """Error raised when context limits are exceeded."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize the error.

        Args:
            message: Human-readable error message
            severity: Error severity level
            category: Error category for classification
            details: Additional error details/context
            cause: Original exception that caused this error
        """
        super().__init__(
            message, severity=severity, category=category, details=details, cause=cause
        )
