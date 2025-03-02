"""Cahoots exception handling system."""

from .api import (
    APIError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ServiceError,
)
from .api import ValidationError as APIValidationError
from .auth import (
    AuthenticationError,
    AuthError,
    AuthorizationError,
    InvalidTokenError,
    RoleError,
)
from .base import AIDTException, CahootsError, ErrorCategory, ErrorSeverity
from .domain import (
    BusinessRuleError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    StateError,
)
from .infrastructure import (
    CacheError,
    DatabaseError,
    ExternalServiceException,
    InfrastructureError,
    NetworkError,
    QueueError,
    StorageError,
)
from .validation import (
    DataValidationError,
    FormatValidationError,
    SchemaValidationError,
    TypeValidationError,
    ValidationError,
)


class ContextLimitError(AIDTException):
    """Raised when context limits are exceeded."""

    pass


__all__ = [
    # Base
    "CahootsError",
    "ErrorCategory",
    "ErrorSeverity",
    # API
    "APIError",
    "NotFoundError",
    "APIValidationError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "ServiceError",
    # Auth
    "AuthError",
    "AuthenticationError",
    "InvalidTokenError",
    "AuthorizationError",
    "RoleError",
    # Infrastructure
    "InfrastructureError",
    "DatabaseError",
    "CacheError",
    "QueueError",
    "StorageError",
    "NetworkError",
    "ExternalServiceException",
    # Domain
    "DomainError",
    "BusinessRuleError",
    "StateError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    # Validation
    "ValidationError",
    "DataValidationError",
    "SchemaValidationError",
    "TypeValidationError",
    "FormatValidationError",
    "ContextLimitError",
]
