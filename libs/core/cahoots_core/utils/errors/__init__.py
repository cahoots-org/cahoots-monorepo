"""Error handling package."""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseError,
    ConfigurationError,
    ConnectionError,
    ContextLimitExceeded,
    DependencyError,
    EventSizeLimitExceeded,
    ExternalServiceException,
    ProcessingError,
    ResourceExistsError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)
from .handling import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    RecoveryStrategy,
    SystemError,
    with_error_handling,
)

__all__ = [
    # Exceptions
    "BaseError",
    "ValidationError",
    "ConfigurationError",
    "ExternalServiceException",
    "ConnectionError",
    "ProcessingError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ResourceExistsError",
    "TimeoutError",
    "DependencyError",
    "ContextLimitExceeded",
    "EventSizeLimitExceeded",
    # Error Handling
    "ErrorSeverity",
    "ErrorCategory",
    "RecoveryStrategy",
    "ErrorContext",
    "SystemError",
    "ErrorHandler",
    "with_error_handling",
]
