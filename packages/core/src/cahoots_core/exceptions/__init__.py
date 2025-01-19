"""Cahoots exception handling system."""

from .base import CahootsError, ErrorCategory, ErrorSeverity
from .api import (
    APIError,
    NotFoundError,
    ValidationError as APIValidationError,
    ConflictError,
    RateLimitError,
    ServerError,
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
] 