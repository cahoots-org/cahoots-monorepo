"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class BaseError(Exception):
    """Base class for all application exceptions."""

    def __init__(
        self, message: str, code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.

        Args:
            message: Error message
            code: Error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary.

        Returns:
            Dict containing error information
        """
        return {"code": self.code, "message": self.message, "details": self.details}


class ValidationError(BaseError):
    """Raised when validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the validation error.

        Args:
            message: Error message
            details: Validation error details
        """
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class ConfigurationError(BaseError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the configuration error.

        Args:
            message: Error message
            details: Configuration error details
        """
        super().__init__(message, code="CONFIG_ERROR", details=details)


class ExternalServiceException(Exception):
    """Raised when an external service call fails."""

    def __init__(self, service: str, operation: str, error: str) -> None:
        """Initialize the external service exception.

        Args:
            service: Name of the external service
            operation: Operation that failed
            error: Error message from the service
        """
        message = f"{service} service error during {operation}: {error}"
        super().__init__(message)
        self.service = service
        self.operation = operation
        self.error = error


class ConnectionError(BaseError):
    """Raised when a connection fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the connection error.

        Args:
            message: Error message
            details: Connection error details
        """
        super().__init__(message, code="CONNECTION_ERROR", details=details)


class ProcessingError(BaseError):
    """Raised when processing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the processing error.

        Args:
            message: Error message
            details: Processing error details
        """
        super().__init__(message, code="PROCESSING_ERROR", details=details)


class AuthenticationError(BaseError):
    """Raised when authentication fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the authentication error.

        Args:
            message: Error message
            details: Authentication error details
        """
        super().__init__(message, code="AUTH_ERROR", details=details)


class AuthorizationError(BaseError):
    """Raised when authorization fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the authorization error.

        Args:
            message: Error message
            details: Authorization error details
        """
        super().__init__(message, code="FORBIDDEN", details=details)


class ResourceNotFoundError(BaseError):
    """Raised when a resource is not found."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the resource not found error.

        Args:
            message: Error message
            details: Resource details
        """
        super().__init__(message, code="NOT_FOUND", details=details)


class ResourceExistsError(BaseError):
    """Raised when a resource already exists."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the resource exists error.

        Args:
            message: Error message
            details: Resource details
        """
        super().__init__(message, code="RESOURCE_EXISTS", details=details)


class TimeoutError(BaseError):
    """Raised when an operation times out."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the timeout error.

        Args:
            message: Error message
            details: Timeout details
        """
        super().__init__(message, code="TIMEOUT", details=details)


class DependencyError(BaseError):
    """Raised when a dependency fails."""

    def __init__(
        self, message: str, dependency_name: str, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the dependency error.

        Args:
            message: Error message
            dependency_name: Name of the failed dependency
            details: Additional error details
        """
        details = details or {}
        details["dependency"] = dependency_name
        super().__init__(message, code="DEPENDENCY_ERROR", details=details)


class ContextLimitExceeded(BaseError):
    """Raised when context size limit is exceeded."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the context limit error.

        Args:
            message: Error message
            details: Context details
        """
        super().__init__(message, code="CONTEXT_LIMIT", details=details)


class EventSizeLimitExceeded(BaseError):
    """Raised when event size limit is exceeded."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the event size limit error.

        Args:
            message: Error message
            details: Event details
        """
        super().__init__(message, code="EVENT_SIZE_LIMIT", details=details)
