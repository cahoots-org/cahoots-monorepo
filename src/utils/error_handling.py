"""Error handling and recovery system."""
from enum import Enum
from typing import Optional, Dict, Any, Type, Callable, List
from dataclasses import dataclass
from datetime import datetime
import logging
import functools
import asyncio
from uuid import UUID, uuid4

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

class SystemError(Exception):
    """Enhanced error class with additional context."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        recovery_strategy: RecoveryStrategy,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context = context
        self.original_error = original_error
        self.retry_count = 0

class ErrorHandler:
    """Centralized error handling and recovery."""
    
    def __init__(self, service_name: str, logger: Optional[logging.Logger] = None):
        self.service_name = service_name
        self.logger = logger or logging.getLogger(__name__)
        self._error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self._recovery_handlers: Dict[RecoveryStrategy, List[Callable]] = {}
        self._circuit_breakers: Dict[str, bool] = {}
        self._error_counts: Dict[str, int] = {}
        
    def handle_error(
        self,
        error: SystemError,
        correlation_id: Optional[UUID] = None,
        **context_data
    ) -> Optional[Any]:
        """Handle an error using appropriate strategy."""
        try:
            # Create error context if not present
            if not error.context:
                error.context = ErrorContext(
                    error_id=uuid4(),
                    timestamp=datetime.utcnow(),
                    service_name=self.service_name,
                    correlation_id=correlation_id,
                    additional_data=context_data
                )
                
            # Log error
            self._log_error(error)
            
            # Check circuit breaker
            if self._is_circuit_open(error):
                raise SystemError(
                    "Circuit breaker open",
                    ErrorCategory.INFRASTRUCTURE,
                    ErrorSeverity.HIGH,
                    RecoveryStrategy.ALERT
                )
                
            # Execute category-specific handlers
            if error.category in self._error_handlers:
                for handler in self._error_handlers[error.category]:
                    try:
                        handler(error)
                    except Exception as e:
                        self.logger.error(f"Error handler failed: {str(e)}")
                        
            # Execute recovery strategy
            if error.recovery_strategy in self._recovery_handlers:
                for handler in self._recovery_handlers[error.recovery_strategy]:
                    try:
                        result = handler(error)
                        if result is not None:
                            return result
                    except Exception as e:
                        self.logger.error(f"Recovery handler failed: {str(e)}")
                        
            # Handle based on strategy
            if error.recovery_strategy == RecoveryStrategy.RETRY:
                return self._handle_retry(error)
            elif error.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAK:
                self._open_circuit(error)
            elif error.recovery_strategy == RecoveryStrategy.TERMINATE:
                raise error
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            raise
            
    def register_error_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[SystemError], None]
    ):
        """Register a handler for specific error category."""
        if category not in self._error_handlers:
            self._error_handlers[category] = []
        self._error_handlers[category].append(handler)
        
    def register_recovery_handler(
        self,
        strategy: RecoveryStrategy,
        handler: Callable[[SystemError], Optional[Any]]
    ):
        """Register a handler for specific recovery strategy."""
        if strategy not in self._recovery_handlers:
            self._recovery_handlers[strategy] = []
        self._recovery_handlers[strategy].append(handler)
        
    def _log_error(self, error: SystemError):
        """Log error with context."""
        self.logger.error(
            f"{error.category.value} error: {str(error)}",
            extra={
                "error_id": str(error.context.error_id),
                "service": error.context.service_name,
                "severity": error.severity.value,
                "category": error.category.value,
                "strategy": error.recovery_strategy.value,
                "correlation_id": str(error.context.correlation_id) if error.context.correlation_id else None,
                "timestamp": error.context.timestamp.isoformat(),
                "additional_data": error.context.additional_data
            }
        )
        
    def _handle_retry(self, error: SystemError) -> Optional[Any]:
        """Handle retry strategy with exponential backoff."""
        max_retries = 3
        if error.retry_count >= max_retries:
            error.recovery_strategy = RecoveryStrategy.CIRCUIT_BREAK
            return None
            
        # Exponential backoff
        delay = (2 ** error.retry_count) * 0.1  # 100ms, 200ms, 400ms
        asyncio.sleep(delay)
        
        error.retry_count += 1
        return True  # Indicate should retry
        
    def _is_circuit_open(self, error: SystemError) -> bool:
        """Check if circuit breaker is open."""
        circuit_key = f"{error.category.value}:{error.context.service_name}"
        return self._circuit_breakers.get(circuit_key, False)
        
    def _open_circuit(self, error: SystemError):
        """Open circuit breaker."""
        circuit_key = f"{error.category.value}:{error.context.service_name}"
        self._circuit_breakers[circuit_key] = True
        self.logger.warning(f"Circuit breaker opened for {circuit_key}")
        
    def _close_circuit(self, error: SystemError):
        """Close circuit breaker."""
        circuit_key = f"{error.category.value}:{error.context.service_name}"
        self._circuit_breakers[circuit_key] = False
        self.logger.info(f"Circuit breaker closed for {circuit_key}")

def with_error_handling(
    category: ErrorCategory,
    severity: ErrorSeverity,
    recovery_strategy: RecoveryStrategy
):
    """Decorator for automatic error handling."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                if isinstance(e, SystemError):
                    raise
                    
                error = SystemError(
                    str(e),
                    category,
                    severity,
                    recovery_strategy,
                    original_error=e
                )
                
                if hasattr(self, "error_handler"):
                    return await self.error_handler.handle_error(error)
                raise error
                
        return wrapper
    return decorator 