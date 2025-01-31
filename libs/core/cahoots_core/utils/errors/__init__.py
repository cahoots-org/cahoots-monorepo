"""Error handling package."""
from .exceptions import (
    BaseError,
    ValidationError,
    ConfigurationError,
    ExternalServiceException,
    ConnectionError,
    ProcessingError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ResourceExistsError,
    TimeoutError,
    DependencyError,
    ContextLimitExceeded,
    EventSizeLimitExceeded
)

from .handling import (
    ErrorSeverity,
    ErrorCategory,
    RecoveryStrategy,
    ErrorContext,
    SystemError,
    ErrorHandler,
    with_error_handling
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
    "with_error_handling"
] 