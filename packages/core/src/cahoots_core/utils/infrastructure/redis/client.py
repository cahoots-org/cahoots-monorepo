"""Redis client for managing Redis connections and operations."""
from typing import Optional, Dict, Any, List, Union
import json
import logging
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

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

class RedisClient:
    """Client for interacting with Redis."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        max_connections: int = 10,
        encoding: str = "utf-8"
    ):
        """Initialize the Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional Redis password
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            max_connections: Maximum number of connections
            encoding: Character encoding
        """
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            max_connections=max_connections,
            encoding=encoding,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.pool)
        
    async def ping(self) -> bool:
        """Test connection to Redis.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            return await self.client.ping()
        except RedisError as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False
            
    async def close(self):
        """Close Redis connection pool."""
        try:
            await self.client.close()
            await self.pool.disconnect()
        except RedisError as e:
            logger.error(f"Error closing Redis connections: {str(e)}")
            raise ConnectionError(f"Failed to close Redis connections: {str(e)}")
            
    async def get(self, key: str) -> Optional[str]:
        """Get value for key.
        
        Args:
            key: Redis key
            
        Returns:
            Value if found, None if not found
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis get failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to get key {key}: {str(e)}")
            
    async def set(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set key to value.
        
        Args:
            key: Redis key
            value: Value to set
            ex: Expiry time in seconds
            px: Expiry time in milliseconds
            nx: Only set if key does not exist
            xx: Only set if key exists
            
        Returns:
            True if set successful, False otherwise
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.set(
                key,
                value,
                ex=ex,
                px=px,
                nx=nx,
                xx=xx
            )
        except RedisError as e:
            logger.error(f"Redis set failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to set key {key}: {str(e)}")
            
    async def delete(self, key: str) -> bool:
        """Delete key.
        
        Args:
            key: Redis key
            
        Returns:
            True if deleted, False if key did not exist
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return bool(await self.client.delete(key))
        except RedisError as e:
            logger.error(f"Redis delete failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to delete key {key}: {str(e)}")
            
    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists, False otherwise
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return bool(await self.client.exists(key))
        except RedisError as e:
            logger.error(f"Redis exists failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to check existence of key {key}: {str(e)}")
            
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiry time.
        
        Args:
            key: Redis key
            seconds: Expiry time in seconds
            
        Returns:
            True if expiry set, False if key does not exist
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis expire failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to set expiry for key {key}: {str(e)}")
            
    async def ttl(self, key: str) -> int:
        """Get key time to live.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds, -2 if key does not exist, -1 if no expiry
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis ttl failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to get TTL for key {key}: {str(e)}")
            
    async def incr(self, key: str) -> int:
        """Increment integer value.
        
        Args:
            key: Redis key
            
        Returns:
            New value
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.incr(key)
        except RedisError as e:
            logger.error(f"Redis incr failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to increment key {key}: {str(e)}")
            
    async def decr(self, key: str) -> int:
        """Decrement integer value.
        
        Args:
            key: Redis key
            
        Returns:
            New value
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.decr(key)
        except RedisError as e:
            logger.error(f"Redis decr failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to decrement key {key}: {str(e)}")
            
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to start of list.
        
        Args:
            key: Redis key
            values: One or more values to push
            
        Returns:
            Length of list after push
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.lpush(key, *values)
        except RedisError as e:
            logger.error(f"Redis lpush failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to push to list {key}: {str(e)}")
            
    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to end of list.
        
        Args:
            key: Redis key
            values: One or more values to push
            
        Returns:
            Length of list after push
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.rpush(key, *values)
        except RedisError as e:
            logger.error(f"Redis rpush failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to push to list {key}: {str(e)}")
            
    async def lpop(self, key: str) -> Optional[str]:
        """Pop value from start of list.
        
        Args:
            key: Redis key
            
        Returns:
            Value if list not empty, None otherwise
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.lpop(key)
        except RedisError as e:
            logger.error(f"Redis lpop failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to pop from list {key}: {str(e)}")
            
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from end of list.
        
        Args:
            key: Redis key
            
        Returns:
            Value if list not empty, None otherwise
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.rpop(key)
        except RedisError as e:
            logger.error(f"Redis rpop failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to pop from list {key}: {str(e)}")
            
    async def llen(self, key: str) -> int:
        """Get length of list.
        
        Args:
            key: Redis key
            
        Returns:
            Length of list
            
        Raises:
            OperationError: If Redis operation fails
        """
        try:
            return await self.client.llen(key)
        except RedisError as e:
            logger.error(f"Redis llen failed for key {key}: {str(e)}")
            raise OperationError(f"Failed to get length of list {key}: {str(e)}")

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
            host=host,
            port=port,
            db=db,
            password=password
        )
    return _redis_client 