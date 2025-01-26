"""Base exception classes for the Cahoots system."""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


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


class ErrorContext:
    """Context information for errors."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
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
            "timestamp": self.timestamp.isoformat()
        }


class CahootsError(Exception):
    """Base exception class for all Cahoots errors.
    
    Provides rich error context and standardized error handling.
    """
    
    def __init__(
        self,
        message: str,
        *args: Any,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize error with context.
        
        Args:
            message: Error message
            severity: Error severity level
            category: Error category
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message, *args)
        self.context = ErrorContext(
            message=message,
            severity=severity,
            category=category,
            details=details
        )
        self.cause = cause
        
    @property
    def message(self) -> str:
        """Get error message."""
        return self.context.message
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        error_dict = self.context.to_dict()
        if self.cause:
            error_dict["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
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
        super().__init__(
            message,
            code=code,
            severity=severity,
            category=category,
            details=details,
            cause=cause
        ) 