"""Custom exceptions for the application."""
from typing import Dict, Any, Optional

class BaseError(Exception):
    """Base class for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
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
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

class ValidationError(BaseError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the validation error.
        
        Args:
            message: Error message
            details: Validation error details
        """
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )

class ConfigurationError(BaseError):
    """Raised when there is a configuration error."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the configuration error.
        
        Args:
            message: Error message
            details: Configuration error details
        """
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details=details
        )

class ExternalServiceException(Exception):
    """Exception raised when an external service call fails."""
    
    def __init__(self, service: str, operation: str, error: str) -> None:
        """Initialize the exception.
        
        Args:
            service: Name of the service that failed
            operation: Name of the operation that failed
            error: Error message
        """
        self.service = service
        self.operation = operation
        self.error = error
        super().__init__(f"{service} service error during {operation}: {error}")

class ConnectionError(BaseError):
    """Raised when a connection fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the connection error.
        
        Args:
            message: Error message
            details: Connection error details
        """
        super().__init__(
            message=message,
            code="CONNECTION_ERROR",
            details=details
        )

class ProcessingError(BaseError):
    """Raised when processing fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the processing error.
        
        Args:
            message: Error message
            details: Processing error details
        """
        super().__init__(
            message=message,
            code="PROCESSING_ERROR",
            details=details
        )

class AuthenticationError(BaseError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the authentication error.
        
        Args:
            message: Error message
            details: Authentication error details
        """
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details
        )

class AuthorizationError(BaseError):
    """Raised when authorization fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the authorization error.
        
        Args:
            message: Error message
            details: Authorization error details
        """
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            details=details
        )

class ResourceNotFoundError(BaseError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the resource not found error.
        
        Args:
            message: Error message
            details: Resource not found error details
        """
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            details=details
        )

class ResourceExistsError(BaseError):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the resource exists error.
        
        Args:
            message: Error message
            details: Resource exists error details
        """
        super().__init__(
            message=message,
            code="RESOURCE_EXISTS",
            details=details
        )

class TimeoutError(BaseError):
    """Raised when an operation times out."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the timeout error.
        
        Args:
            message: Error message
            details: Timeout error details
        """
        super().__init__(
            message=message,
            code="TIMEOUT_ERROR",
            details=details
        )

class DependencyError(BaseError):
    """Raised when a required dependency is missing or invalid."""
    
    def __init__(
        self,
        message: str,
        dependency_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the dependency error.
        
        Args:
            message: Error message
            dependency_name: Name of the missing/invalid dependency
            details: Additional error details
        """
        super().__init__(
            message=message,
            code="DEPENDENCY_ERROR",
            details={"dependency": dependency_name, **(details or {})}
        ) 