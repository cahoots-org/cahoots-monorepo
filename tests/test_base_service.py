"""Tests for the base service module.

This module contains tests for the BaseService class and related components:
- CircuitBreakerState: Circuit breaker pattern implementation
- ServiceResponse: HTTP response wrapper
- BaseService: Base class for all service clients
"""
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_mock import MockFixture

from src.services.base_service import (
    BaseService,
    CircuitBreakerState,
    ServiceResponse,
    ServiceConfig
)
from src.core.dependencies import ServiceDeps

# Test constants
TEST_SERVICE_NAME = "test-service"
TEST_SERVICE_URL = "http://test-service.local"
TEST_TIMEOUT = 5
TEST_RETRY_ATTEMPTS = 3
TEST_RETRY_DELAY = 1
TEST_FAILURE_THRESHOLD = 3
TEST_RESET_TIMEOUT = 30

# Test data
TEST_RESPONSE_DATA = {"key": "value"}
TEST_ERROR_MESSAGE = "Test error"

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.settings = MagicMock()
    deps.db = AsyncMock()
    deps.redis = AsyncMock()
    deps.event_system = AsyncMock()
    return deps

@pytest.fixture
def service_config() -> ServiceConfig:
    """Create a service configuration for testing."""
    return ServiceConfig(
        name=TEST_SERVICE_NAME,
        url=TEST_SERVICE_URL,
        timeout=TEST_TIMEOUT,
        retry_attempts=TEST_RETRY_ATTEMPTS,
        retry_delay=TEST_RETRY_DELAY
    )

@pytest.fixture
def base_service(service_config: ServiceConfig, mock_deps: ServiceDeps) -> BaseService:
    """Create a base service instance for testing."""
    return BaseService(service_config, deps=mock_deps)

@pytest.fixture
def mock_response() -> Mock:
    """Create a mock HTTP response.
    
    Returns:
        Mock: Response mock with standard test data.
    """
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.content = b'{"key": "value"}'
    response.json.return_value = TEST_RESPONSE_DATA
    return response

@pytest.fixture
def circuit_breaker() -> CircuitBreakerState:
    """Create a circuit breaker instance for testing.
    
    Returns:
        CircuitBreakerState: Configured circuit breaker.
    """
    return CircuitBreakerState(
        failure_threshold=TEST_FAILURE_THRESHOLD,
        reset_timeout=TEST_RESET_TIMEOUT
    )

@pytest.fixture(autouse=True)
def mock_sleep() -> AsyncGenerator[None, None]:
    """Mock asyncio.sleep to speed up tests.
    
    Yields:
        None
    """
    with patch("asyncio.sleep", return_value=None):
        yield

@pytest.fixture(autouse=True)
def mock_metrics() -> AsyncGenerator[None, None]:
    """Mock service metrics to avoid side effects.
    
    Yields:
        None
    """
    with patch("src.services.base_service.SERVICE_REQUEST_COUNTER.labels", return_value=Mock()), \
         patch("src.services.base_service.SERVICE_REQUEST_TIME.labels", return_value=Mock()), \
         patch("src.services.base_service.SERVICE_ERROR_COUNTER.labels", return_value=Mock()), \
         patch("src.services.base_service.CIRCUIT_BREAKER_STATE.labels", return_value=Mock()), \
         patch("src.services.base_service.CIRCUIT_BREAKER_FAILURES.labels", return_value=Mock()):
        yield

class TestCircuitBreaker:
    """Tests for the CircuitBreakerState class."""
    
    def test_init(self, circuit_breaker: CircuitBreakerState) -> None:
        """Test circuit breaker initialization with default values."""
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.failure_threshold == TEST_FAILURE_THRESHOLD
        assert circuit_breaker.reset_timeout == TEST_RESET_TIMEOUT
        assert circuit_breaker.last_failure_time is None
        assert not circuit_breaker.is_open
    
    def test_record_failure_until_open(self, circuit_breaker: CircuitBreakerState) -> None:
        """Test failure recording until circuit opens."""
        # Record failures up to threshold
        for i in range(circuit_breaker.failure_threshold - 1):
            circuit_breaker.record_failure()
            assert not circuit_breaker.is_open
            assert circuit_breaker.failure_count == i + 1
        
        # Record one more failure to open circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.is_open
        assert circuit_breaker.failure_count == circuit_breaker.failure_threshold
        assert circuit_breaker.last_failure_time is not None
    
    def test_record_success_resets_state(self, circuit_breaker: CircuitBreakerState) -> None:
        """Test success recording resets circuit breaker state."""
        # First record some failures
        for _ in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure()
        
        # Record success should reset state
        circuit_breaker.record_success()
        assert not circuit_breaker.is_open
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time is None
    
    def test_should_allow_request_timing(self, circuit_breaker: CircuitBreakerState) -> None:
        """Test request allowance based on timing."""
        # Initially should allow requests
        assert circuit_breaker.should_allow_request()
        
        # Open circuit
        for _ in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure()
        
        # Should not allow requests when circuit is freshly opened
        assert not circuit_breaker.should_allow_request()
        
        # Should allow requests after timeout
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(
            seconds=circuit_breaker.reset_timeout + 1
        )
        assert circuit_breaker.should_allow_request()

class TestServiceResponse:
    """Tests for the ServiceResponse class."""
    
    def test_success_response_creation(self) -> None:
        """Test successful response object creation."""
        response = ServiceResponse(
            success=True,
            data=TEST_RESPONSE_DATA,
            status_code=200
        )
        assert response.success
        assert response.data == TEST_RESPONSE_DATA
        assert response.status_code == 200
        assert response.error is None
    
    def test_error_response_creation(self) -> None:
        """Test error response object creation."""
        response = ServiceResponse(
            success=False,
            error=TEST_ERROR_MESSAGE,
            status_code=500
        )
        assert not response.success
        assert response.error == TEST_ERROR_MESSAGE
        assert response.status_code == 500
        assert response.data is None

class TestBaseService:
    """Tests for the BaseService class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, base_service: BaseService, mock_deps: ServiceDeps) -> None:
        """Test service initialization with configuration."""
        assert base_service.config.name == TEST_SERVICE_NAME
        assert base_service.logger is not None
        assert isinstance(base_service.circuit_breaker, CircuitBreakerState)
        assert base_service._client is None
        assert base_service.deps is mock_deps
    
    @pytest.mark.asyncio
    async def test_client_creation_and_reuse(self, base_service: BaseService) -> None:
        """Test HTTP client creation and reuse pattern."""
        # First call should create new client
        client1 = await base_service.get_client()
        assert isinstance(client1, httpx.AsyncClient)
        
        # Second call should return same client
        client2 = await base_service.get_client()
        assert client2 is client1
    
    @pytest.mark.asyncio
    async def test_client_cleanup(self, base_service: BaseService) -> None:
        """Test client cleanup on service close."""
        # Create and verify client
        client = await base_service.get_client()
        assert base_service._client is not None
        
        # Close and verify cleanup
        await base_service.close()
        assert base_service._client is None
    
    @pytest.mark.asyncio
    async def test_successful_request(
        self,
        base_service: BaseService,
        mock_response: Mock,
        mock_deps: ServiceDeps
    ) -> None:
        """Test successful HTTP request handling."""
        with patch("httpx.AsyncClient.request", AsyncMock(return_value=mock_response)):
            response = await base_service._make_request("GET", "/test")
            
            assert response.success
            assert response.data == TEST_RESPONSE_DATA
            assert response.status_code == 200
            mock_deps.event_system.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_retry_logic(
        self,
        base_service: BaseService,
        mock_response: Mock,
        mock_deps: ServiceDeps
    ) -> None:
        """Test request retry behavior with exponential backoff."""
        error_response = Mock(spec=httpx.Response)
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = httpx.HTTPError(TEST_ERROR_MESSAGE)
        
        sleep_times = []
        
        async def mock_sleep(delay: float):
            sleep_times.append(delay)
        
        with patch("httpx.AsyncClient.request") as mock_request, \
             patch("asyncio.sleep", mock_sleep):
            mock_request.side_effect = [
                error_response,  # First attempt fails
                error_response,  # Second attempt fails
                mock_response   # Third attempt succeeds
            ]
            
            response = await base_service._make_request("GET", "/test")
            
            assert response.success
            assert response.data == TEST_RESPONSE_DATA
            assert mock_request.call_count == 3
            mock_deps.event_system.emit.assert_called()
            
            # Verify exponential backoff pattern
            assert len(sleep_times) == 2  # Two retries
            assert 0.75 <= sleep_times[0] <= 1.25  # First retry: ~1s ±25%
            assert 1.5 <= sleep_times[1] <= 2.5    # Second retry: ~2s ±25%
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, base_service: BaseService, mock_deps: ServiceDeps) -> None:
        """Test request handling when circuit breaker is open."""
        # Open the circuit breaker
        base_service.circuit_breaker.failure_count = 5
        base_service.circuit_breaker.is_open = True
        base_service.circuit_breaker.last_failure_time = datetime.utcnow()
        
        response = await base_service._make_request("GET", "/test")
        
        assert not response.success
        assert response.status_code == 503
        assert "Circuit breaker is open" in response.error
        mock_deps.event_system.emit.assert_called()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(
        self,
        base_service: BaseService,
        mock_response: Mock,
        mock_deps: ServiceDeps
    ) -> None:
        """Test circuit breaker half-open state and recovery."""
        # Set circuit breaker to open state but with old failure time
        base_service.circuit_breaker.failure_count = 5
        base_service.circuit_breaker.is_open = True
        base_service.circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=61)
        
        with patch("httpx.AsyncClient.request", AsyncMock(return_value=mock_response)):
            response = await base_service._make_request("GET", "/test")
            
            assert response.success
            assert not base_service.circuit_breaker.is_open
            assert base_service.circuit_breaker.failure_count == 0
            mock_deps.event_system.emit.assert_called()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, base_service: BaseService) -> None:
        """Test behavior when max retries are exceeded."""
        error_response = Mock(spec=httpx.Response)
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = httpx.HTTPError(TEST_ERROR_MESSAGE)
        
        with patch("httpx.AsyncClient.request", AsyncMock(return_value=error_response)), \
             patch("asyncio.sleep", AsyncMock()):
            response = await base_service._make_request("GET", "/test")
            
            assert not response.success
            assert response.status_code == 500
            assert "Max retries exceeded" in response.error 