"""Error handling and recovery system."""
from enum import Enum
from typing import Optional, Dict, Any, Type, Callable, List
from dataclasses import dataclass
from datetime import datetime
import logging
import functools
import asyncio
from uuid import UUID, uuid4

from .exceptions import BaseError

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Non-critical errors that don't affect core functionality
    MEDIUM = "medium"     # Errors that degrade service but don't stop it
    HIGH = "high"         # Errors that prevent specific functionality
    CRITICAL = "critical" # Errors that could crash the service

class ErrorCategory(Enum):
    """Categories of errors for better handling."""
    VALIDATION = "validation"       # Input validation errors
    BUSINESS_LOGIC = "business"     # Business rule violations
    INFRASTRUCTURE = "infrastructure" # System/network/resource errors
    SECURITY = "security"          # Security-related errors
    TIMEOUT = "timeout"            # Timeout errors
    DEPENDENCY = "dependency"      # External service/dependency errors
    DATA = "data"                  # Data integrity/consistency errors
    SYSTEM = "system"             # System-level errors
    UNKNOWN = "unknown"            # Uncategorized errors

class RecoveryStrategy(Enum):
    """Strategies for error recovery."""
    RETRY = "retry"               # Retry the operation
    CIRCUIT_BREAK = "break"       # Stop trying and fail fast
    FALLBACK = "fallback"         # Use alternative method/value
    IGNORE = "ignore"             # Continue despite error
    ALERT = "alert"               # Alert but continue
    TERMINATE = "terminate"       # Stop processing

@dataclass
class ErrorContext:
    """Context information for errors."""
    error_id: UUID
    timestamp: datetime
    service_name: str
    correlation_id: Optional[UUID] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class SystemError(BaseError):
    """System-level error with context and recovery information."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        recovery_strategy: RecoveryStrategy,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize system error.
        
        Args:
            message: Error message
            category: Error category
            severity: Error severity level
            recovery_strategy: Recovery strategy to use
            context: Error context information
            original_error: Original exception if this wraps another error
        """
        super().__init__(
            message,
            code=f"{category.value.upper()}_ERROR",
            details={
                "severity": severity.value,
                "recovery_strategy": recovery_strategy.value,
                "context": context.__dict__ if context else None,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.category = category
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context = context
        self.original_error = original_error

class ErrorHandler:
    """Handles system errors with configurable recovery strategies."""
    
    def __init__(self, service_name: str, logger: Optional[logging.Logger] = None):
        """Initialize error handler.
        
        Args:
            service_name: Name of the service
            logger: Optional logger instance
        """
        self.service_name = service_name
        self.logger = logger or logging.getLogger(__name__)
        self._error_handlers: Dict[ErrorCategory, List[Callable[[SystemError], None]]] = {}
        self._recovery_handlers: Dict[RecoveryStrategy, List[Callable[[SystemError], Optional[Any]]]] = {}
        self._circuit_breakers: Dict[str, bool] = {}
    
    def handle_error(
        self,
        error: SystemError,
        correlation_id: Optional[UUID] = None,
        **context_data
    ) -> Optional[Any]:
        """Handle a system error.
        
        Args:
            error: System error to handle
            correlation_id: Optional correlation ID
            **context_data: Additional context data
            
        Returns:
            Optional recovery result
        """
        if not error.context:
            error.context = ErrorContext(
                error_id=uuid4(),
                timestamp=datetime.utcnow(),
                service_name=self.service_name,
                correlation_id=correlation_id,
                additional_data=context_data
            )
        
        self._log_error(error)
        
        # Execute category-specific handlers
        handlers = self._error_handlers.get(error.category, [])
        for handler in handlers:
            try:
                handler(error)
            except Exception as e:
                self.logger.error(f"Error handler failed: {str(e)}")
        
        # Execute recovery strategy
        if error.recovery_strategy == RecoveryStrategy.RETRY:
            return self._handle_retry(error)
        elif error.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAK:
            if self._is_circuit_open(error):
                raise error
            self._open_circuit(error)
            raise error
        elif error.recovery_strategy == RecoveryStrategy.FALLBACK:
            handlers = self._recovery_handlers.get(RecoveryStrategy.FALLBACK, [])
            for handler in handlers:
                try:
                    result = handler(error)
                    if result is not None:
                        return result
                except Exception as e:
                    self.logger.error(f"Recovery handler failed: {str(e)}")
        elif error.recovery_strategy == RecoveryStrategy.TERMINATE:
            raise error
        
        return None
    
    def register_error_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[SystemError], None]
    ):
        """Register an error handler for a specific category.
        
        Args:
            category: Error category to handle
            handler: Handler function
        """
        if category not in self._error_handlers:
            self._error_handlers[category] = []
        self._error_handlers[category].append(handler)
    
    def register_recovery_handler(
        self,
        strategy: RecoveryStrategy,
        handler: Callable[[SystemError], Optional[Any]]
    ):
        """Register a recovery handler for a specific strategy.
        
        Args:
            strategy: Recovery strategy to handle
            handler: Handler function
        """
        if strategy not in self._recovery_handlers:
            self._recovery_handlers[strategy] = []
        self._recovery_handlers[strategy].append(handler)
    
    def _log_error(self, error: SystemError):
        """Log error details.
        
        Args:
            error: Error to log
        """
        log_data = {
            "error_id": error.context.error_id if error.context else None,
            "correlation_id": error.context.correlation_id if error.context else None,
            "category": error.category.value,
            "severity": error.severity.value,
            "recovery_strategy": error.recovery_strategy.value,
            "original_error": str(error.original_error) if error.original_error else None
        }
        
        if error.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            self.logger.error(f"{error.message}", extra=log_data)
        else:
            self.logger.warning(f"{error.message}", extra=log_data)
    
    def _handle_retry(self, error: SystemError) -> Optional[Any]:
        """Handle retry recovery strategy.
        
        Args:
            error: Error to retry
            
        Returns:
            Optional recovery result
        """
        handlers = self._recovery_handlers.get(RecoveryStrategy.RETRY, [])
        for handler in handlers:
            try:
                result = handler(error)
                if result is not None:
                    return result
            except Exception as e:
                self.logger.error(f"Retry handler failed: {str(e)}")
        return None
    
    def _is_circuit_open(self, error: SystemError) -> bool:
        """Check if circuit breaker is open.
        
        Args:
            error: Error to check
            
        Returns:
            True if circuit is open
        """
        return self._circuit_breakers.get(f"{error.category.value}_{error.severity.value}", False)
    
    def _open_circuit(self, error: SystemError):
        """Open circuit breaker.
        
        Args:
            error: Error that triggered circuit break
        """
        self._circuit_breakers[f"{error.category.value}_{error.severity.value}"] = True
    
    def _close_circuit(self, error: SystemError):
        """Close circuit breaker.
        
        Args:
            error: Error associated with circuit
        """
        self._circuit_breakers[f"{error.category.value}_{error.severity.value}"] = False

def with_error_handling(
    category: ErrorCategory,
    severity: ErrorSeverity,
    recovery_strategy: RecoveryStrategy
):
    """Decorator for error handling.
    
    Args:
        category: Error category
        severity: Error severity
        recovery_strategy: Recovery strategy
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                if isinstance(e, SystemError):
                    error = e
                else:
                    error = SystemError(
                        str(e),
                        category,
                        severity,
                        recovery_strategy,
                        original_error=e
                    )
                
                if hasattr(self, "error_handler") and isinstance(self.error_handler, ErrorHandler):
                    return self.error_handler.handle_error(error)
                raise error
        return wrapper
    return decorator 