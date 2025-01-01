import asyncio
import httpx
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..utils.config import ServiceConfig
from ..utils.logger import Logger
from ..utils.metrics import (
    SERVICE_REQUEST_COUNTER,
    SERVICE_REQUEST_TIME,
    SERVICE_ERROR_COUNTER,
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_FAILURES,
    track_time
)

class CircuitBreakerState:
    """Circuit breaker state tracking"""
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False

    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True

    def record_success(self):
        """Record a success and reset the failure count"""
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None

    def should_allow_request(self) -> bool:
        """Check if a request should be allowed"""
        if not self.is_open:
            return True
            
        if self.last_failure_time is None:
            return True
            
        # Check if enough time has passed to try again
        if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
            self.is_open = False
            return True
            
        return False

class ServiceResponse(BaseModel):
    """Standard service response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None

class BaseService:
    """Base class for service interactions with retry and circuit breaker patterns"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.logger = Logger(f"Service-{config.name}")
        self.circuit_breaker = CircuitBreakerState()
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                verify=True  # Enable SSL verification
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @track_time(SERVICE_REQUEST_TIME, {'service': 'config.name', 'method': 'method'})
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ServiceResponse:
        """Make HTTP request with retry and circuit breaker logic"""
        if not self.circuit_breaker.should_allow_request():
            CIRCUIT_BREAKER_STATE.labels(service=self.config.name).set(1)
            return ServiceResponse(
                success=False,
                error="Circuit breaker is open",
                status_code=503
            )

        CIRCUIT_BREAKER_STATE.labels(service=self.config.name).set(0)
        client = await self.get_client()
        retry_count = 0
        last_error = None

        while retry_count <= self.config.retry_attempts:
            try:
                if retry_count > 0:
                    await asyncio.sleep(self.config.retry_delay * (2 ** (retry_count - 1)))

                SERVICE_REQUEST_COUNTER.labels(
                    service=self.config.name,
                    method=method,
                    endpoint=endpoint
                ).inc()

                response = await client.request(
                    method=method,
                    url=f"{self.config.url}{endpoint}",
                    json=data,
                    headers=headers
                )
                
                response.raise_for_status()
                self.circuit_breaker.record_success()
                
                return ServiceResponse(
                    success=True,
                    data=response.json() if response.content else None,
                    status_code=response.status_code
                )

            except httpx.HTTPError as e:
                last_error = str(e)
                if response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                    CIRCUIT_BREAKER_FAILURES.labels(service=self.config.name).inc()
                retry_count += 1
                SERVICE_ERROR_COUNTER.labels(
                    service=self.config.name,
                    error_type="http_error"
                ).inc()
                self.logger.error(f"Request failed (attempt {retry_count}): {str(e)}")

            except Exception as e:
                last_error = str(e)
                self.circuit_breaker.record_failure()
                CIRCUIT_BREAKER_FAILURES.labels(service=self.config.name).inc()
                retry_count += 1
                SERVICE_ERROR_COUNTER.labels(
                    service=self.config.name,
                    error_type="unexpected_error"
                ).inc()
                self.logger.error(f"Unexpected error (attempt {retry_count}): {str(e)}")

        return ServiceResponse(
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
            status_code=500
        )

    async def get(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> ServiceResponse:
        """Make GET request"""
        return await self._make_request("GET", endpoint, headers=headers)

    async def post(self, endpoint: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> ServiceResponse:
        """Make POST request"""
        return await self._make_request("POST", endpoint, data=data, headers=headers)

    async def put(self, endpoint: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> ServiceResponse:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, data=data, headers=headers)

    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> ServiceResponse:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint, headers=headers) 