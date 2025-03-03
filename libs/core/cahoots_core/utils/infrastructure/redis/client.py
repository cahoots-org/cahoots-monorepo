"""Redis client for managing Redis connections and operations."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from ...metrics.timing import track_time
from ..base import BaseClient, BaseConfig

logger = logging.getLogger(__name__)


class RedisClientError(Exception):
    """Base exception for Redis client errors."""

    pass


class ConnectionError(RedisClientError):
    """Exception raised for Redis connection errors."""

    pass


class OperationError(RedisClientError):
    """Exception raised for Redis operation errors."""

    pass


@dataclass
class RedisConfig(BaseConfig):
    """Redis client configuration."""

    url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    encoding: str = "utf-8"


class RedisClient(BaseClient[RedisConfig]):
    """Redis client implementation."""

    def __init__(self, config: RedisConfig):
        """Initialize Redis client.

        Args:
            config: Redis configuration
        """
        super().__init__(config)
        self._client: Optional[Redis] = None
        self._connected = False

    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if not self._client or not self._connected:
            raise ConnectionError("Redis client not initialized or not connected")
        return self._client

    @track_time(metric="redis_connect")
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            connection_kwargs = {"encoding": self.config.encoding, "decode_responses": True}

            # Add SSL configuration if enabled
            if self.config.ssl:
                connection_kwargs["ssl_cert_reqs"] = None

            if self.config.url:
                self._client = redis_from_url(self.config.url, **connection_kwargs)
            else:
                self._client = Redis(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    **connection_kwargs,
                )

            # Verify connection
            await self.verify_connection()
            self._connected = True

        except Exception as e:
            self._client = None
            self._connected = False
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False

    @track_time(metric="redis_ping")
    async def verify_connection(self) -> bool:
        """Verify Redis connection is active."""
        try:
            if not self._client:
                return False

            result = await self._client.ping()
            return result == True

        except Exception as e:
            logger.error(f"Redis connection verification failed: {str(e)}")
            return False

    async def ping(self) -> bool:
        """Ping Redis server to verify connection.

        Returns:
            True if connection is active, False otherwise
        """
        return await self.verify_connection()

    @track_time(metric="redis_get")
    async def get(self, key: str) -> Any:
        """Get value from Redis.

        Args:
            key: Key to get

        Returns:
            Value if found, None otherwise
        """
        return await self.retry_operation(
            self.client.get, key, retry_on=(RedisError,), operation_name=f"get:{key}"
        )

    @track_time(metric="redis_set")
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value in Redis.

        Args:
            key: Key to set
            value: Value to set
            expire: Optional expiration in seconds
        """
        await self.retry_operation(
            self.client.set,
            key,
            value,
            ex=expire,
            retry_on=(RedisError,),
            operation_name=f"set:{key}",
        )

    @track_time(metric="redis_delete")
    async def delete(self, key: str) -> None:
        """Delete key from Redis.

        Args:
            key: Key to delete
        """
        await self.retry_operation(
            self.client.delete, key, retry_on=(RedisError,), operation_name=f"delete:{key}"
        )

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Key to check

        Returns:
            True if exists, False otherwise
        """
        return await self.retry_operation(
            self.client.exists, key, retry_on=(RedisError,), operation_name=f"exists:{key}"
        )

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration.

        Args:
            key: Key to set expiration for
            seconds: Expiration in seconds

        Returns:
            True if expiration was set, False if key doesn't exist
        """
        return await self.retry_operation(
            self.client.expire, key, seconds, retry_on=(RedisError,), operation_name=f"expire:{key}"
        )

    async def ttl(self, key: str) -> int:
        """Get key time to live.

        Args:
            key: Key to get TTL for

        Returns:
            TTL in seconds, -2 if key doesn't exist, -1 if no expiry
        """
        return await self.retry_operation(
            self.client.ttl, key, retry_on=(RedisError,), operation_name=f"ttl:{key}"
        )

    @track_time(metric="redis_incr")
    async def incr(self, key: str) -> int:
        """Increment key value.

        Args:
            key: Key to increment

        Returns:
            New value after increment
        """
        return await self.retry_operation(
            self.client.incr, key, retry_on=(RedisError,), operation_name=f"incr:{key}"
        )

    @track_time(metric="redis_decr")
    async def decr(self, key: str) -> int:
        """Decrement key value.

        Args:
            key: Key to decrement

        Returns:
            New value after decrement
        """
        return await self.retry_operation(
            self.client.decr, key, retry_on=(RedisError,), operation_name=f"decr:{key}"
        )

    @track_time(metric="redis_lpush")
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the head of a list.

        Args:
            key: List key
            values: Values to push

        Returns:
            Length of list after push
        """
        return await self.retry_operation(
            self.client.lpush, key, *values, retry_on=(RedisError,), operation_name=f"lpush:{key}"
        )

    @track_time(metric="redis_rpush")
    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to the tail of a list.

        Args:
            key: List key
            values: Values to push

        Returns:
            Length of list after push
        """
        return await self.retry_operation(
            self.client.rpush, key, *values, retry_on=(RedisError,), operation_name=f"rpush:{key}"
        )

    @track_time(metric="redis_lpop")
    async def lpop(self, key: str) -> Optional[str]:
        """Pop value from the head of a list.

        Args:
            key: List key

        Returns:
            Value if list exists and not empty, None otherwise
        """
        return await self.retry_operation(
            self.client.lpop, key, retry_on=(RedisError,), operation_name=f"lpop:{key}"
        )

    @track_time(metric="redis_rpop")
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from the tail of a list.

        Args:
            key: List key

        Returns:
            Value if list exists and not empty, None otherwise
        """
        return await self.retry_operation(
            self.client.rpop, key, retry_on=(RedisError,), operation_name=f"rpop:{key}"
        )

    @track_time(metric="redis_llen")
    async def llen(self, key: str) -> int:
        """Get length of a list.

        Args:
            key: List key

        Returns:
            Length of list, 0 if key doesn't exist
        """
        return await self.retry_operation(
            self.client.llen, key, retry_on=(RedisError,), operation_name=f"llen:{key}"
        )


# Global client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client(
    url: Optional[str] = None, max_retries: int = 3, retry_interval: int = 1
) -> "RedisClient":
    """Get Redis client instance with retries.

    Args:
        url: Redis URL
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds between retries

    Returns:
        Initialized Redis client

    Raises:
        ConnectionError: If connection fails after retries
    """
    config = RedisConfig(url=url)
    client = RedisClient(config)

    async def initialize():
        for attempt in range(max_retries):
            try:
                await client.connect()
                return client
            except Exception as e:
                logger.error(
                    f"Redis connection attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_interval)
                else:
                    raise ConnectionError(f"Could not connect to Redis: {str(e)}")

    try:
        return asyncio.get_event_loop().run_until_complete(initialize())
    except Exception as e:
        raise ConnectionError(f"Could not connect to Redis: {str(e)}")
