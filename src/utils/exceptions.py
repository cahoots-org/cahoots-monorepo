"""Custom exceptions for the application."""

class BaseAppException(Exception):
    """Base exception class for the application."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ExternalServiceException(BaseAppException):
    """Exception raised when an external service call fails."""
    def __init__(self, service: str, operation: str, error: str, details: dict = None):
        self.service = service
        self.operation = operation
        message = f"{service} service error during {operation}: {error}"
        super().__init__(message, details)

class ValidationException(BaseAppException):
    """Exception raised when validation fails."""
    pass

class ConfigurationException(BaseAppException):
    """Exception raised when configuration is invalid."""
    pass

class AuthenticationException(BaseAppException):
    """Exception raised when authentication fails."""
    pass

class AuthorizationException(BaseAppException):
    """Exception raised when authorization fails."""
    pass

class RateLimitException(BaseAppException):
    """Exception raised when rate limit is exceeded."""
    pass

class ResourceNotFoundException(BaseAppException):
    """Exception raised when a requested resource is not found."""
    pass

class DuplicateResourceException(BaseAppException):
    """Exception raised when attempting to create a duplicate resource."""
    pass

class InvalidStateException(BaseAppException):
    """Exception raised when an operation is invalid for the current state."""
    pass

class PayloadTooLargeException(BaseAppException):
    """Exception raised when request payload exceeds size limit."""
    def __init__(self, max_size: int, actual_size: int):
        message = f"Payload size {actual_size} bytes exceeds maximum of {max_size} bytes"
        details = {
            "max_size": max_size,
            "actual_size": actual_size
        }
        super().__init__(message, details)

class ServiceUnavailableException(BaseAppException):
    """Exception raised when a service is temporarily unavailable."""
    def __init__(self, service_name: str = "Unknown", details: dict = None):
        message = f"Service {service_name} is temporarily unavailable"
        super().__init__(message, details)

class RateLimitExceededException(BaseAppException):
    """Exception raised when API rate limit is exceeded."""
    def __init__(self, limit: int, window: int, retry_after: int = None):
        message = f"Rate limit of {limit} requests per {window} seconds exceeded"
        details = {
            "limit": limit,
            "window": window,
            "retry_after": retry_after
        }
        super().__init__(message, details) 