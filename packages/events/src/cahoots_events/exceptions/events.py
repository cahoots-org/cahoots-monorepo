"""Event-specific exceptions."""
from typing import Optional, Dict, Any

from .base import CahootsError, ErrorCategory, ErrorSeverity


class EventError(CahootsError):
    """Base class for event-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        category: ErrorCategory = ErrorCategory.DOMAIN,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ):
        """Initialize event error.
        
        Args:
            message: Error message
            details: Additional error details
            category: Error category
            severity: Error severity
        """
        super().__init__(
            message=message,
            details=details,
            category=category,
            severity=severity
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