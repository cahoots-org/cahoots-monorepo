"""Redis client for storage operations."""

import json
import asyncio
from typing import Any, Optional, List, Dict, Union
from datetime import datetime, timezone

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError, ResponseError


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class RedisClient:
    """Redis client for caching and state management."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        test_mode: bool = False,
        test_client: Optional[Any] = None
    ):
        """Initialize Redis client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional Redis password
            test_mode: Whether to use test mode
            test_client: Optional test client (for unit tests)
        """
        if test_mode and test_client:
            self.redis = test_client
            self.test_mode = True
        else:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                retry=Retry(ExponentialBackoff(), 3),
            )
            self.test_mode = False

    async def connect(self) -> None:
        """Test the connection to Redis."""
        if not self.test_mode:
            await self.redis.ping()

    async def close(self) -> None:
        """Close the Redis connection."""
        if not self.test_mode:
            await self.redis.close()

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set a key-value pair in Redis.

        Args:
            key: The key to set
            value: The value to set
            expire: Optional expiration in seconds

        Returns:
            True if successful
        """
        try:
            if not isinstance(value, str):
                json_value = json.dumps(value, cls=DateTimeEncoder)
            else:
                json_value = value

            if expire:
                await self.redis.set(key, json_value, ex=expire)
            else:
                await self.redis.set(key, json_value)
            return True
        except Exception as e:
            print(f"Error setting key {key}: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis by key.

        Args:
            key: The key to get

        Returns:
            The value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            print(f"Error getting key {key}: {e}")
            raise

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of keys that exist
        """
        return await self.redis.exists(*keys)

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern.

        Args:
            pattern: Pattern to match (default: *)

        Returns:
            List of matching keys
        """
        return await self.redis.keys(pattern)

    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values by keys.

        Args:
            keys: List of keys to get

        Returns:
            List of values (None for missing keys)
        """
        values = await self.redis.mget(keys)
        result = []
        for value in values:
            if value:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)
            else:
                result.append(None)
        return result

    async def mset(self, mapping: Dict[str, Any]) -> bool:
        """Set multiple key-value pairs.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        encoded_mapping = {}
        for key, value in mapping.items():
            if not isinstance(value, str):
                encoded_mapping[key] = json.dumps(value, cls=DateTimeEncoder)
            else:
                encoded_mapping[key] = value

        return await self.redis.mset(encoded_mapping)

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter.

        Args:
            key: The counter key
            amount: Amount to increment by (default: 1)

        Returns:
            The new counter value
        """
        return await self.redis.incr(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key.

        Args:
            key: The key to expire
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set
        """
        return await self.redis.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get time-to-live for a key.

        Args:
            key: The key to check

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        return await self.redis.ttl(key)

    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list.

        Args:
            key: The list key
            values: Values to push

        Returns:
            The length of the list after push
        """
        encoded_values = []
        for value in values:
            if not isinstance(value, str):
                encoded_values.append(json.dumps(value, cls=DateTimeEncoder))
            else:
                encoded_values.append(value)
        return await self.redis.lpush(key, *encoded_values)

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to the right of a list.

        Args:
            key: The list key
            values: Values to push

        Returns:
            The length of the list after push
        """
        encoded_values = []
        for value in values:
            if not isinstance(value, str):
                encoded_values.append(json.dumps(value, cls=DateTimeEncoder))
            else:
                encoded_values.append(value)
        return await self.redis.rpush(key, *encoded_values)

    async def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Get a range of elements from a list.

        Args:
            key: The list key
            start: Start index
            stop: Stop index (-1 for end)

        Returns:
            List of elements
        """
        values = await self.redis.lrange(key, start, stop)
        result = []
        for value in values:
            try:
                result.append(json.loads(value))
            except json.JSONDecodeError:
                result.append(value)
        return result

    async def llen(self, key: str) -> int:
        """Get the length of a list.

        Args:
            key: The list key

        Returns:
            Length of the list
        """
        return await self.redis.llen(key)

    # Set operations
    async def sadd(self, key: str, *values: Any) -> int:
        """Add members to a set.

        Args:
            key: The set key
            values: Values to add

        Returns:
            Number of elements added
        """
        encoded_values = []
        for value in values:
            if not isinstance(value, str):
                encoded_values.append(json.dumps(value, cls=DateTimeEncoder))
            else:
                encoded_values.append(value)
        return await self.redis.sadd(key, *encoded_values)

    async def smembers(self, key: str) -> set:
        """Get all members of a set.

        Args:
            key: The set key

        Returns:
            Set of members
        """
        values = await self.redis.smembers(key)
        result = set()
        for value in values:
            try:
                result.add(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                result.add(value)
        return result

    async def scard(self, key: str) -> int:
        """Get the cardinality of a set.

        Args:
            key: The set key

        Returns:
            Number of members in the set
        """
        return await self.redis.scard(key)

    async def sismember(self, key: str, value: Any) -> bool:
        """Check if value is a member of set.

        Args:
            key: The set key
            value: Value to check

        Returns:
            True if value is a member
        """
        if not isinstance(value, str):
            value = json.dumps(value, cls=DateTimeEncoder)
        return await self.redis.sismember(key, value)

    async def srem(self, key: str, *values: Any) -> int:
        """Remove members from a set.

        Args:
            key: The set key
            values: Values to remove

        Returns:
            Number of elements removed
        """
        encoded_values = []
        for value in values:
            if not isinstance(value, str):
                encoded_values.append(json.dumps(value, cls=DateTimeEncoder))
            else:
                encoded_values.append(value)
        return await self.redis.srem(key, *encoded_values)