"""Tests for the error handling system."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.utils.error_handler import (
    ErrorHandler,
    ErrorContext,
    ErrorSeverity,
    ErrorCategory,
    BaseError,
    ValidationError,
    ConfigurationError,
    ConnectionError,
    AuthenticationError,
    AuthorizationError,
    ResourceError,
    BusinessLogicError
)

@pytest.fixture
def error_handler():
    """Create an error handler instance."""
    return ErrorHandler()

@pytest.fixture
def error_context():
    """Create a sample error context."""
    return ErrorContext(
        timestamp=datetime.utcnow(),
        component="test_component",
        operation="test_operation",
        input_data={"test": "data"},
        user_id="test_user",
        trace_id="test_trace",
        additional_info={"extra": "info"}
    )

def test_error_context_creation(error_context):
    """Test error context creation."""
    assert error_context.component == "test_component"
    assert error_context.operation == "test_operation"
    assert error_context.input_data == {"test": "data"}
    assert error_context.user_id == "test_user"
    assert error_context.trace_id == "test_trace"
    assert error_context.additional_info == {"extra": "info"}
    assert isinstance(error_context.timestamp, datetime)

def test_base_error_creation(error_context):
    """Test base error creation."""
    error = BaseError(
        message="Test error",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.SYSTEM,
        context=error_context
    )
    
    assert error.message == "Test error"
    assert error.severity == ErrorSeverity.ERROR
    assert error.category == ErrorCategory.SYSTEM
    assert error.context == error_context
    assert error.cause is None
    assert error.traceback is None

def test_base_error_with_cause(error_context):
    """Test base error with cause."""
    cause = ValueError("Original error")
    error = BaseError(
        message="Wrapped error",
        cause=cause,
        context=error_context
    )
    
    assert error.message == "Wrapped error"
    assert error.cause == cause
    assert error.traceback is not None

def test_base_error_to_dict(error_context):
    """Test base error serialization."""
    cause = ValueError("Original error")
    error = BaseError(
        message="Test error",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.SYSTEM,
        context=error_context,
        cause=cause
    )
    
    error_dict = error.to_dict()
    assert error_dict["message"] == "Test error"
    assert error_dict["severity"] == "error"
    assert error_dict["category"] == "system"
    assert "timestamp" in error_dict
    
    context_dict = error_dict["context"]
    assert context_dict["component"] == "test_component"
    assert context_dict["operation"] == "test_operation"
    assert context_dict["input_data"] == {"test": "data"}
    
    cause_dict = error_dict["cause"]
    assert cause_dict["type"] == "ValueError"
    assert cause_dict["message"] == "Original error"
    assert "traceback" in cause_dict

def test_specific_errors(error_context):
    """Test specific error types."""
    # Validation error
    validation_error = ValidationError("Invalid input", error_context)
    assert validation_error.severity == ErrorSeverity.WARNING
    assert validation_error.category == ErrorCategory.VALIDATION
    
    # Configuration error
    config_error = ConfigurationError("Bad config", error_context)
    assert config_error.severity == ErrorSeverity.ERROR
    assert config_error.category == ErrorCategory.CONFIGURATION
    
    # Connection error
    conn_error = ConnectionError("Connection failed", error_context)
    assert conn_error.severity == ErrorSeverity.ERROR
    assert conn_error.category == ErrorCategory.CONNECTION
    
    # Authentication error
    auth_error = AuthenticationError("Invalid credentials", error_context)
    assert auth_error.severity == ErrorSeverity.ERROR
    assert auth_error.category == ErrorCategory.AUTHENTICATION
    
    # Authorization error
    authz_error = AuthorizationError("Insufficient permissions", error_context)
    assert authz_error.severity == ErrorSeverity.ERROR
    assert authz_error.category == ErrorCategory.AUTHORIZATION
    
    # Resource error
    resource_error = ResourceError("Resource not found", error_context)
    assert resource_error.severity == ErrorSeverity.ERROR
    assert resource_error.category == ErrorCategory.RESOURCE
    
    # Business logic error
    business_error = BusinessLogicError("Invalid operation", error_context)
    assert business_error.severity == ErrorSeverity.ERROR
    assert business_error.category == ErrorCategory.BUSINESS_LOGIC

def test_error_handler_handle_base_error(error_handler, error_context):
    """Test handling BaseError."""
    error = BaseError("Test error", context=error_context)
    response = error_handler.handle(error)
    
    assert response["status"] == "error"
    assert response["message"] == "Test error"
    assert "error" in response
    assert response["error"]["message"] == "Test error"
    assert response["error"]["severity"] == "error"
    assert response["error"]["category"] == "unknown"

def test_error_handler_handle_unknown_error(error_handler, error_context):
    """Test handling unknown error type."""
    error = ValueError("Unknown error")
    response = error_handler.handle(error, error_context)
    
    assert response["status"] == "error"
    assert response["message"] == "Unknown error"
    assert response["error"]["category"] == "unknown"
    assert response["error"]["severity"] == "error"

def test_error_handler_with_logger(error_handler, error_context):
    """Test error handler logging."""
    with patch.object(error_handler.logger, 'error') as mock_logger:
        error = BaseError("Test error", context=error_context)
        error_handler.handle(error)
        
        mock_logger.assert_called_once()
        args = mock_logger.call_args[0]
        assert "UNKNOWN: Test error" in args

def test_error_handler_create_context(error_handler):
    """Test creating error context."""
    context = error_handler.create_error_context(
        component="test",
        operation="test_op",
        input_data={"test": "data"},
        user_id="user1",
        trace_id="trace1",
        additional_info={"extra": "info"}
    )
    
    assert isinstance(context, ErrorContext)
    assert context.component == "test"
    assert context.operation == "test_op"
    assert context.input_data == {"test": "data"}
    assert context.user_id == "user1"
    assert context.trace_id == "trace1"
    assert context.additional_info == {"extra": "info"}
    assert isinstance(context.timestamp, datetime)

def test_error_severity_values():
    """Test error severity enum values."""
    assert ErrorSeverity.DEBUG.value == "debug"
    assert ErrorSeverity.INFO.value == "info"
    assert ErrorSeverity.WARNING.value == "warning"
    assert ErrorSeverity.ERROR.value == "error"
    assert ErrorSeverity.CRITICAL.value == "critical"

def test_error_category_values():
    """Test error category enum values."""
    assert ErrorCategory.VALIDATION.value == "validation"
    assert ErrorCategory.CONFIGURATION.value == "configuration"
    assert ErrorCategory.CONNECTION.value == "connection"
    assert ErrorCategory.AUTHENTICATION.value == "authentication"
    assert ErrorCategory.AUTHORIZATION.value == "authorization"
    assert ErrorCategory.RESOURCE.value == "resource"
    assert ErrorCategory.BUSINESS_LOGIC.value == "business_logic"
    assert ErrorCategory.SYSTEM.value == "system"
    assert ErrorCategory.EXTERNAL.value == "external"
    assert ErrorCategory.UNKNOWN.value == "unknown" 