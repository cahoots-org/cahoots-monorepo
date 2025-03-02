"""Exceptions for the context package."""

from typing import Any, Dict, Optional

from cahoots_core.exceptions import CahootsError
from cahoots_core.exceptions.base import ErrorCategory, ErrorSeverity


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
