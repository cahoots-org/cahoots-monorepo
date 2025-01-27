"""Cahoots exception handling system."""

from .base import CahootsError, ErrorCategory, ErrorSeverity, AIDTException
from .api import (
    APIError,
    NotFoundError,
    ValidationError as APIValidationError,
    ConflictError,
    RateLimitError,
    ServerError,
    ServiceError,
)
from .auth import (
    AuthError,
    AuthenticationError,
    InvalidTokenError,
    AuthorizationError,
    RoleError,
)
from .infrastructure import (
    InfrastructureError,
    DatabaseError,
    CacheError,
    QueueError,
    StorageError,
    NetworkError,
    ExternalServiceException,
)
from .domain import (
    DomainError,
    BusinessRuleError,
    StateError,
    EntityNotFoundError,
    DuplicateEntityError,
)
from .validation import (
    ValidationError,
    DataValidationError,
    SchemaValidationError,
    TypeValidationError,
    FormatValidationError,
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
    "ContextLimitError"
] 