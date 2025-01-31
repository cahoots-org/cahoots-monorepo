"""Redis client for managing Redis connections and operations."""
from typing import Optional, Dict, Any, List, Union
import json
import logging
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError
from redis.asyncio import Redis, from_url as redis_from_url
from dataclasses import dataclass

from ..base import BaseConfig, BaseClient
from ...metrics.timing import track_time

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
        
    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if not self._client:
            raise ConnectionError("Redis client not initialized")
        return self._client
        
    @track_time(metric="redis_connect")
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            if self.config.url:
                self._client = redis_from_url(
                    self.config.url,
                    encoding=self.config.encoding,
                    decode_responses=True,
                    ssl=self.config.ssl,
                    socket_timeout=self.config.timeout
                )
            else:
                self._client = Redis(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    encoding=self.config.encoding,
                    decode_responses=True,
                    ssl=self.config.ssl,
                    socket_timeout=self.config.timeout
                )
            
            # Verify connection
            await self.verify_connection()
            self._connected = True
            
        except Exception as e:
            self._handle_error(e, "connect")
            
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
                
            await self._client.ping()
            return True
            
        except Exception as e:
            self._handle_error(e, "verify_connection")
            
    @track_time(metric="redis_get")
    async def get(self, key: str) -> Any:
        """Get value from Redis.
        
        Args:
            key: Key to get
            
        Returns:
            Value if found, None otherwise
        """
        return await self.retry_operation(
            self.client.get,
            key,
            retry_on=(RedisError,),
            operation_name=f"get:{key}"
        )
            
    @track_time(metric="redis_set")
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> None:
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
            operation_name=f"set:{key}"
        )
            
    @track_time(metric="redis_delete")
    async def delete(self, key: str) -> None:
        """Delete key from Redis.
        
        Args:
            key: Key to delete
        """
        await self.retry_operation(
            self.client.delete,
            key,
            retry_on=(RedisError,),
            operation_name=f"delete:{key}"
        )
            
    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Key to check
            
        Returns:
            True if exists, False otherwise
        """
        return await self.retry_operation(
            self.client.exists,
            key,
            retry_on=(RedisError,),
            operation_name=f"exists:{key}"
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
            self.client.expire,
            key,
            seconds,
            retry_on=(RedisError,),
            operation_name=f"expire:{key}"
        )
            
    async def ttl(self, key: str) -> int:
        """Get key time to live.
        
        Args:
            key: Key to get TTL for
            
        Returns:
            TTL in seconds, -2 if key doesn't exist, -1 if no expiry
        """
        return await self.retry_operation(
            self.client.ttl,
            key,
            retry_on=(RedisError,),
            operation_name=f"ttl:{key}"
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
            self.client.incr,
            key,
            retry_on=(RedisError,),
            operation_name=f"incr:{key}"
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
            self.client.decr,
            key,
            retry_on=(RedisError,),
            operation_name=f"decr:{key}"
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
            self.client.lpush,
            key,
            *values,
            retry_on=(RedisError,),
            operation_name=f"lpush:{key}"
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
            self.client.rpush,
            key,
            *values,
            retry_on=(RedisError,),
            operation_name=f"rpush:{key}"
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
            self.client.lpop,
            key,
            retry_on=(RedisError,),
            operation_name=f"lpop:{key}"
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
            self.client.rpop,
            key,
            retry_on=(RedisError,),
            operation_name=f"rpop:{key}"
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
            self.client.llen,
            key,
            retry_on=(RedisError,),
            operation_name=f"llen:{key}"
        )

# Global client instance
_redis_client: Optional[RedisClient] = None

def get_redis_client(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> RedisClient:
    """Get or create the global Redis client instance.
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Optional Redis password
        
    Returns:
        RedisClient instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(
            RedisConfig(
            host=host,
            port=port,
            db=db,
            password=password
            )
        )
    return _redis_client 