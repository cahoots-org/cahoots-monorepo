"""Infrastructure exceptions for the Cahoots system."""
from typing import Any, Dict, Optional

from .base import CahootsError, ErrorCategory, ErrorSeverity


class InfrastructureError(CahootsError):
    """Base class for infrastructure-related errors."""
    
    def __init__(
        self,
        message: str,
        *,
        service: Optional[str] = None,
        **kwargs
    ):
        """Initialize infrastructure error.
        
        Args:
            message: Error message
            service: Name of the infrastructure service
            **kwargs: Additional arguments passed to CahootsError
        """
        super().__init__(
            message,
            category=ErrorCategory.INFRASTRUCTURE,
            details={"service": service, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class DatabaseError(InfrastructureError):
    """Database-related errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="DATABASE_ERROR",
            service="database",
            severity=ErrorSeverity.ERROR,
            details={"operation": operation, **(kwargs.pop("details", {}) or {})},
            **kwargs
        )


class CacheError(InfrastructureError):
    """Cache-related errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="CACHE_ERROR",
            service="cache",
            severity=ErrorSeverity.WARNING,
            details={
                "operation": operation,
                "key": key,
                **(kwargs.pop("details", {}) or {})
            },
            **kwargs
        )


class QueueError(InfrastructureError):
    """Queue-related errors."""
    
    def __init__(
        self,
        message: str,
        queue_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="QUEUE_ERROR",
            service="queue",
            severity=ErrorSeverity.ERROR,
            details={
                "queue_name": queue_name,
                "operation": operation,
                **(kwargs.pop("details", {}) or {})
            },
            **kwargs
        )


class StorageError(InfrastructureError):
    """Storage-related errors."""
    
    def __init__(
        self,
        message: str,
        storage_type: Optional[str] = None,
        operation: Optional[str] = None,
        path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="STORAGE_ERROR",
            service="storage",
            severity=ErrorSeverity.ERROR,
            details={
                "storage_type": storage_type,
                "operation": operation,
                "path": path,
                **(kwargs.pop("details", {}) or {})
            },
            **kwargs
        )


class NetworkError(InfrastructureError):
    """Network-related errors."""
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            code="NETWORK_ERROR",
            service="network",
            severity=ErrorSeverity.ERROR,
            details={
                "host": host,
                "port": port,
                **(kwargs.pop("details", {}) or {})
            },
            **kwargs
        ) 