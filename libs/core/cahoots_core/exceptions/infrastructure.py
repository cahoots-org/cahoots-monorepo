"""Infrastructure-related exceptions."""

from typing import Any, Dict, Optional

from .base import CahootsError, ErrorCategory, ErrorSeverity


class InfrastructureError(CahootsError):
    """Base class for infrastructure-related errors."""

    def __init__(
        self,
        message: str,
        *args: Any,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            *args,
            severity=severity,
            category=ErrorCategory.INFRASTRUCTURE,
            details=details,
            cause=cause,
        )


class ClientError(InfrastructureError):
    """Base class for client-related errors."""

    pass


class DatabaseError(ClientError):
    """Database-related errors."""

    pass


class CacheError(ClientError):
    """Cache-related errors."""

    pass


class QueueError(ClientError):
    """Message queue-related errors."""

    pass


class StorageError(ClientError):
    """Storage-related errors."""

    def __init__(
        self,
        message: str,
        *args: Any,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize storage error.

        Args:
            message: Error message
            operation: Storage operation that failed
            severity: Error severity
            details: Additional error details
            cause: Optional exception that caused the error
        """
        if details is None:
            details = {}
        details["operation"] = operation
        super().__init__(message, *args, severity=severity, details=details, cause=cause)


class NetworkError(InfrastructureError):
    """Network-related errors."""

    pass


class ConnectionError(NetworkError):
    """Connection-related errors."""

    pass


class TimeoutError(NetworkError):
    """Timeout-related errors."""

    pass


class ConfigurationError(InfrastructureError):
    """Configuration-related errors."""

    pass


class ResourceError(InfrastructureError):
    """Resource-related errors."""

    pass


class ResourceNotFoundError(ResourceError):
    """Resource not found errors."""

    pass


class ResourceExistsError(ResourceError):
    """Resource already exists errors."""

    pass


class ExternalServiceError(InfrastructureError):
    """External service integration errors."""

    pass


class ExternalServiceException(InfrastructureError):
    """Exception raised when an external service call fails."""

    def __init__(
        self,
        message: str,
        *,
        service: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"service": service, "operation": operation, **(details or {})},
            cause=cause,
        )
