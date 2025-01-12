"""Cache management with multi-level caching."""
from typing import Any, Dict, Optional, TypeVar, Generic, List, Callable, Set
from collections import OrderedDict, defaultdict
import json
import asyncio
import logging
import random
from datetime import datetime, timedelta
from redis import Redis
from functools import wraps

from .error_handling import SystemError, ErrorCategory, ErrorSeverity, RecoveryStrategy
from .version_vector import VersionVector

T = TypeVar('T')

class CacheEntry(Generic[T]):
    def __init__(
        self,
        value: T,
        ttl: int,
        version: int = 1,
        last_updated: Optional[datetime] = None,
        access_count: int = 0,
        last_accessed: Optional[datetime] = None
    ):
        self.value = value
        self.ttl = ttl
        self.version = version
        self.last_updated = last_updated or datetime.utcnow()
        self.access_count = access_count
        self.last_accessed = last_accessed or datetime.utcnow()
        
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.last_updated + timedelta(seconds=self.ttl)
        
    def record_access(self) -> None:
        """Record cache access for predictive warming."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        value = self.value
        if isinstance(value, VersionVector):
            value = value.to_dict()
        return {
            "value": value,
            "ttl": self.ttl,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict, value_type: Optional[type] = None) -> 'CacheEntry[T]':
        value = data["value"]
        if value_type == VersionVector and isinstance(value, dict):
            vector = VersionVector(versions=value.get("versions", {}))
            if "timestamp" in value:
                vector.timestamp = datetime.fromisoformat(value["timestamp"])
            value = vector
        return cls(
            value=value,
            ttl=data["ttl"],
            version=data["version"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data.get(
                "last_accessed",
                data["last_updated"]
            ))
        )

class LRUCache(Generic[T]):
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.pattern_window = timedelta(hours=24)
        
    def get(self, key: str) -> Optional[T]:
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            return None
            
        # Record access for pattern analysis
        entry.record_access()
        self.access_patterns[key].append(datetime.utcnow())
        self._clean_old_patterns(key)
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return entry.value
        
    def put(self, key: str, value: T, ttl: int) -> None:
        if key in self.cache:
            # Update existing entry
            entry = self.cache[key]
            entry.value = value
            entry.last_updated = datetime.utcnow()
            self.cache.move_to_end(key)
        else:
            # Add new entry
            if len(self.cache) >= self.capacity:
                # Remove least recently used
                self.cache.popitem(last=False)
            self.cache[key] = CacheEntry(value, ttl)
            
    def get_access_pattern(self, key: str) -> List[datetime]:
        """Get access pattern for predictive warming."""
        return self.access_patterns.get(key, [])
        
    def _clean_old_patterns(self, key: str) -> None:
        """Clean up old access pattern data."""
        cutoff = datetime.utcnow() - self.pattern_window
        self.access_patterns[key] = [
            ts for ts in self.access_patterns[key]
            if ts > cutoff
        ]

class CacheManager:
    def __init__(
        self,
        redis: Redis,
        local_cache_size: int = 1000,
        default_ttl: int = 3600,
        warmup_threshold: int = 10
    ):
        self.redis = redis
        self.local_cache: LRUCache = LRUCache(local_cache_size)
        self.default_ttl = default_ttl
        self.warmup_threshold = warmup_threshold
        self.logger = logging.getLogger(__name__)
        self._invalidation_callbacks: Dict[str, List[Callable]] = {}
        self._warmup_tasks: Set[asyncio.Task] = set()
        self._running = True
        
    async def get(
        self,
        key: str,
        default: Any = None,
        ttl: Optional[int] = None,
        value_type: Optional[type] = None
    ) -> Any:
        """Get value from cache, trying local cache first then Redis."""
        # Try local cache first
        if value := self.local_cache.get(key):
            return value
            
        # Try Redis
        try:
            data = await self.redis.get(key)
            if not data:
                return default
                
            entry = CacheEntry.from_dict(json.loads(data), value_type)
            if entry.is_expired():
                await self.delete(key)
                return default
                
            # Update local cache
            self.local_cache.put(key, entry.value, entry.ttl)
            return entry.value
            
        except Exception as e:
            self.logger.error(f"Error reading from Redis cache: {str(e)}")
            return default
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        version: Optional[int] = None
    ) -> None:
        """Set value in both local and Redis cache."""
        ttl = ttl or self.default_ttl
        
        try:
            # Create new entry with version 1 for new values
            entry = CacheEntry(
                value=value,
                ttl=ttl,
                version=1  # Always start with version 1 for new values
            )
            
            # Update Redis
            await self.redis.setex(
                key,
                ttl,
                json.dumps(entry.to_dict())
            )
            
            # Update local cache
            self.local_cache.put(key, value, ttl)
            
        except Exception as e:
            raise SystemError(
                message=f"Failed to set cache value: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY,
                original_error=e,
                context={"cache_key": key}
            )
            
    async def delete(self, key: str) -> None:
        """Delete value from both caches."""
        try:
            await self.redis.delete(key)
            if key in self.local_cache.cache:
                del self.local_cache.cache[key]
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {str(e)}")

def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    key_builder: Optional[Callable] = None,
    value_type: Optional[type] = None
):
    """Cache decorator that supports async Redis operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager instance from first arg (self)
            if not args:
                raise ValueError("Cached function must be a method")
            cache_manager = args[0].cache_manager
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default to using function args as key
                key_parts = [key_prefix, func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                
            # Try to get from cache
            cached_value = await cache_manager.get(
                cache_key,
                value_type=value_type
            )
            if cached_value is not None:
                return cached_value
                
            # Call function if cache miss
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_manager.set(
                cache_key,
                result,
                ttl=ttl
            )
            
            return result
        return wrapper
    return decorator 