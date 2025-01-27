"""Domain-related exceptions."""
from typing import Optional, Dict, Any

from .base import CahootsError, ErrorCategory, ErrorSeverity

class DomainError(CahootsError):
    """Base class for domain-related errors."""
    
    def __init__(
        self,
        message: str,
        *args: Any,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message,
            *args,
            severity=severity,
            category=ErrorCategory.BUSINESS,
            details=details,
            cause=cause
        )

class BusinessRuleError(DomainError):
    """Error raised when a business rule is violated."""
    pass

class StateError(DomainError):
    """Error raised when an object is in an invalid state."""
    pass

class EntityNotFoundError(DomainError):
    """Error raised when an entity cannot be found."""
    
    def __init__(
        self,
        message: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize entity not found error.
        
        Args:
            message: Error message
            entity_type: Type of entity that was not found
            entity_id: ID of entity that was not found
            details: Additional error details
        """
        if details is None:
            details = {}
        details.update({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.WARNING
        )

class DuplicateEntityError(DomainError):
    """Error raised when attempting to create a duplicate entity."""
    
    def __init__(
        self,
        message: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize duplicate entity error.
        
        Args:
            message: Error message
            entity_type: Type of entity that was duplicated
            entity_id: ID of entity that was duplicated
            details: Additional error details
        """
        if details is None:
            details = {}
        details.update({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.ERROR
        ) 