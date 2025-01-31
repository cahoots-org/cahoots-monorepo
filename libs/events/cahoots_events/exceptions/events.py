"""Event-specific exceptions."""
from typing import Optional, Dict, Any

from .base import CahootsError, ErrorCategory, ErrorSeverity


class EventError(CahootsError):
    """Base class for event-related errors."""
    
    def __init__(
        self,
        message: str,
        *args: Any,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.BUSINESS,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize event error.
        
        Args:
            message: Error message
            severity: Error severity
            category: Error category
            details: Additional error details
            cause: Optional exception that caused the error
        """
        super().__init__(
            message,
            *args,
            severity=severity,
            category=category,
            details=details,
            cause=cause
        )


class EventPublishError(EventError):
    """Error raised when publishing an event fails."""
    pass


class EventSubscriptionError(EventError):
    """Error raised when subscribing to events fails."""
    pass


class EventHandlingError(EventError):
    """Error raised when handling an event fails."""
    pass


class EventValidationError(EventError):
    """Error raised when event validation fails."""
    pass


class EventSizeLimitExceeded(EventError):
    """Error raised when event size exceeds the limit."""
    
    def __init__(
        self,
        message: str,
        size: int,
        limit: int,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize size limit exceeded error.
        
        Args:
            message: Error message
            size: Actual size of the event
            limit: Maximum allowed size
            details: Additional error details
        """
        if details is None:
            details = {}
        details.update({
            "size": size,
            "limit": limit,
            "exceeded_by": size - limit
        })
        super().__init__(
            message=message,
            details=details,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR
        ) 