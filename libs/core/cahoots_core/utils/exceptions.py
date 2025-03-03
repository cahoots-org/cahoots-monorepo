"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class AIDTException(Exception):
    """Base exception class for all application exceptions."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format.

        Returns:
            Dict[str, Any]: Exception details
        """
        return {"error": self.__class__.__name__, "message": str(self), "details": self.details}


class ValidationError(AIDTException):
    """Raised when data validation fails."""

    pass


class EventError(AIDTException):
    """Base class for event-related errors."""

    pass


class EventHandlingError(EventError):
    """Raised when event handling fails."""

    pass


class EventSubscriptionError(EventError):
    """Raised when event subscription fails."""

    pass


class ModelError(AIDTException):
    """Base class for model-related errors."""

    pass


class ModelGenerationError(ModelError):
    """Raised when model generation fails."""

    pass


class TestError(AIDTException):
    """Base class for test-related errors."""

    pass


class TestExecutionError(TestError):
    """Raised when test execution fails."""

    pass


class TestTimeoutError(TestError):
    """Raised when test execution times out."""

    pass


class ContextError(AIDTException):
    """Base class for context-related errors."""

    pass


class ContextLimitExceeded(ContextError):
    """Raised when context limit is exceeded."""

    pass


class ServiceError(AIDTException):
    """Base class for service-related errors."""

    pass


class ServiceConfigError(ServiceError):
    """Raised when service configuration is invalid."""

    pass


class ServiceConnectionError(ServiceError):
    """Raised when service connection fails."""

    pass


class ServiceOperationError(ServiceError):
    """Raised when service operation fails."""

    pass
