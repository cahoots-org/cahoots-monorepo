"""Unified error handling module."""
from typing import Dict, Any, Optional, Type
from enum import Enum
import traceback
from datetime import datetime
from dataclasses import dataclass
from .logger import Logger

class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories."""
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESOURCE = "resource"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL = "external"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Error context information."""
    timestamp: datetime
    component: str
    operation: str
    input_data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

class BaseError(Exception):
    """Base error class."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize error.
        
        Args:
            message: Error message
            severity: Error severity level
            category: Error category
            context: Error context information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context
        self.cause = cause
        self.traceback = traceback.format_exc() if cause else None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format.
        
        Returns:
            Dict[str, Any]: Error details
        """
        error_dict = {
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.context:
            error_dict["context"] = {
                "timestamp": self.context.timestamp.isoformat(),
                "component": self.context.component,
                "operation": self.context.operation,
                "input_data": self.context.input_data,
                "user_id": self.context.user_id,
                "trace_id": self.context.trace_id,
                "additional_info": self.context.additional_info
            }
            
        if self.cause:
            error_dict["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
                "traceback": self.traceback
            }
            
        return error_dict

class ValidationError(BaseError):
    """Validation error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=cause
        )

class ConfigurationError(BaseError):
    """Configuration error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            cause=cause
        )

class ConnectionError(BaseError):
    """Connection error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.CONNECTION,
            context=context,
            cause=cause
        )

class AuthenticationError(BaseError):
    """Authentication error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.AUTHENTICATION,
            context=context,
            cause=cause
        )

class AuthorizationError(BaseError):
    """Authorization error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.AUTHORIZATION,
            context=context,
            cause=cause
        )

class ResourceError(BaseError):
    """Resource error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=context,
            cause=cause
        )

class BusinessLogicError(BaseError):
    """Business logic error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.BUSINESS_LOGIC,
            context=context,
            cause=cause
        )

class ErrorHandler:
    """Central error handler."""
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = Logger("ErrorHandler")
        
    def handle(self, error: Exception, context: Optional[ErrorContext] = None) -> Dict[str, Any]:
        """Handle an error.
        
        Args:
            error: Exception to handle
            context: Optional error context
            
        Returns:
            Dict[str, Any]: Error response
        """
        if isinstance(error, BaseError):
            base_error = error
        else:
            # Wrap unknown exceptions
            base_error = BaseError(
                str(error),
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.UNKNOWN,
                context=context,
                cause=error
            )
            
        # Log error
        log_method = getattr(
            self.logger,
            base_error.severity.value,
            self.logger.error
        )
        log_method(
            f"{base_error.category.value.upper()}: {base_error.message}",
            error_details=base_error.to_dict()
        )
        
        # Return error response
        return {
            "error": base_error.to_dict(),
            "status": "error",
            "message": base_error.message
        }
        
    def create_error_context(
        self,
        component: str,
        operation: str,
        input_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Create error context.
        
        Args:
            component: Component where error occurred
            operation: Operation being performed
            input_data: Optional input data that caused error
            user_id: Optional user ID
            trace_id: Optional trace ID
            additional_info: Optional additional context
            
        Returns:
            ErrorContext: Error context object
        """
        return ErrorContext(
            timestamp=datetime.utcnow(),
            component=component,
            operation=operation,
            input_data=input_data,
            user_id=user_id,
            trace_id=trace_id,
            additional_info=additional_info
        )

# Global error handler instance
error_handler = ErrorHandler() 