"""Tests for utility decorators."""
import pytest
from unittest.mock import Mock
from src.utils.decorators import service_error_handler
from src.utils.exceptions import ExternalServiceException

@pytest.fixture
def mock_counter():
    """Create a mock metric counter."""
    counter = Mock()
    counter.labels.return_value = counter
    return counter

@pytest.mark.asyncio
async def test_service_error_handler_success():
    """Test successful function execution."""
    @service_error_handler("TestService")
    async def test_func():
        return "success"
        
    result = await test_func()
    assert result == "success"

@pytest.mark.asyncio
async def test_service_error_handler_exception(mock_counter):
    """Test exception handling and metrics."""
    @service_error_handler(
        "TestService",
        metric_counter=mock_counter,
        method="GET",
        endpoint="/test"
    )
    async def test_func():
        raise ValueError("test error")
        
    with pytest.raises(ExternalServiceException) as exc_info:
        await test_func()
        
    assert exc_info.value.service == "TestService"
    assert exc_info.value.operation == "test_func"
    assert str(exc_info.value) == "TestService service error during test_func: test error"
    
    mock_counter.labels.assert_called_once_with(
        method="GET",
        endpoint="/test",
        status_code="500"
    )
    mock_counter.inc.assert_called_once()

@pytest.mark.asyncio
async def test_service_error_handler_passthrough():
    """Test that ExternalServiceException is re-raised without wrapping."""
    original_error = ExternalServiceException(
        service="TestService",
        operation="test_op",
        error="original error"
    )
    
    @service_error_handler("TestService")
    async def test_func():
        raise original_error
        
    with pytest.raises(ExternalServiceException) as exc_info:
        await test_func()
        
    assert exc_info.value is original_error 