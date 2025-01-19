"""Base exceptions for the Cahoots system."""
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
    """Categories of errors for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INFRASTRUCTURE = "infrastructure"
    DOMAIN = "domain"
    API = "api"
    UNKNOWN = "unknown"


class CahootsError(Exception):
    """Base exception for all Cahoots errors.
    
    All custom exceptions should inherit from this class to ensure
    consistent error handling and logging across the system.
    """
    
    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
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
        super().__init__(message)
        self.message = message
        self.code = code
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.cause = cause
        
    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{self.code}: {self.message}"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format.
        
        Useful for logging and API responses.
        """
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        } 