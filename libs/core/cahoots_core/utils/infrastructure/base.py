"""Base infrastructure client implementation."""

import abc
import asyncio
import logging
from contextlib import AbstractAsyncContextManager
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar

from ...exceptions.infrastructure import (
    ClientError,
    ConfigurationError,
    ConnectionError,
    TimeoutError,
)
from ...utils.metrics.timing import track_time

T = TypeVar("T")
R = TypeVar("R")


class BaseConfig:
    """Base configuration for infrastructure clients."""

    def __init__(
        self,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        retry_max_delay: float = 30.0,
    ):
        """Initialize configuration.

        Args:
            timeout: Operation timeout in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Initial delay between retries in seconds
            retry_backoff: Multiplier for delay after each retry
            retry_max_delay: Maximum delay between retries
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.retry_max_delay = retry_max_delay


class BaseClient(AbstractAsyncContextManager, Generic[T]):
    """Base class for infrastructure clients.

    Provides common functionality for:
    - Configuration management
    - Connection lifecycle
    - Error handling
    - Metrics collection
    - Retries
    """

    def __init__(self, config: T, logger: Optional[logging.Logger] = None):
        """Initialize client.

        Args:
            config: Client configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def connect(self) -> None:
        """Establish connection.

        Should be implemented by subclasses.

        Raises:
            ConnectionError: If connection fails
            ConfigurationError: If configuration is invalid
            TimeoutError: If connection times out
        """
        raise NotImplementedError

    async def disconnect(self) -> None:
        """Close connection.

        Should be implemented by subclasses.
        """
        raise NotImplementedError

    async def verify_connection(self) -> bool:
        """Verify connection is active.

        Should be implemented by subclasses.

        Returns:
            bool: True if connected, False otherwise
        """
        raise NotImplementedError

    async def __aenter__(self) -> "BaseClient[T]":
        """Enter async context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.disconnect()

    @track_time(metric="retry_operation")
    async def retry_operation(
        self,
        operation: Callable[..., Awaitable[R]],
        *args: Any,
        retry_on: tuple[type[Exception], ...] = (Exception,),
        operation_name: Optional[str] = None,
        **kwargs: Any,
    ) -> R:
        """Execute operation with retry logic.

        Args:
            operation: Async function to execute
            *args: Positional arguments for operation
            retry_on: Tuple of exception types to retry on
            operation_name: Name of operation for logging
            **kwargs: Keyword arguments for operation

        Returns:
            Result of operation

        Raises:
            ClientError: If all retries fail
        """
        op_name = operation_name or operation.__name__
        delay = self.config.retry_delay
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                return await operation(*args, **kwargs)

            except retry_on as e:
                last_error = e
                if attempt == self.config.retry_attempts - 1:
                    break

                self.logger.warning(
                    f"{op_name} failed (attempt {attempt + 1}/{self.config.retry_attempts}): {str(e)}"
                )

                # Wait before retry with exponential backoff
                await asyncio.sleep(min(delay, self.config.retry_max_delay))
                delay *= self.config.retry_backoff

        # All retries failed
        self._handle_error(
            last_error or Exception(f"{op_name} failed with no error"),
            op_name,
            {"attempts": self.config.retry_attempts},
        )

    def _handle_error(
        self, error: Exception, operation: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle client error.

        Args:
            error: Original exception
            operation: Operation being performed
            details: Additional error details

        Raises:
            ClientError: Wrapped client error
        """
        error_details = {"operation": operation, **(details or {})}

        if isinstance(error, TimeoutError):
            raise TimeoutError(
                f"Operation {operation} timed out", details=error_details, cause=error
            )

        if isinstance(error, ConnectionError):
            raise ConnectionError(
                f"Connection error during {operation}", details=error_details, cause=error
            )

        raise ClientError(
            f"Error during {operation}: {str(error)}", details=error_details, cause=error
        )
