"""Cache management with multi-level caching and predictive warming."""
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
        return {
            "value": self.value,
            "ttl": self.ttl,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry[T]':
        return cls(
            value=data["value"],
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
        self._start_warmup_monitor()
        
    def _start_warmup_monitor(self) -> None:
        """Start background task for predictive cache warming."""
        async def monitor_patterns():
            while self._running:
                try:
                    await self._check_warmup_patterns()
                except Exception as e:
                    self.logger.error(f"Error in warmup monitor: {str(e)}")
                await asyncio.sleep(300)  # Check every 5 minutes
                
        asyncio.create_task(monitor_patterns())
        
    async def _check_warmup_patterns(self) -> None:
        """Check access patterns and pre-warm frequently accessed keys."""
        for key, entry in self.local_cache.cache.items():
            pattern = self.local_cache.get_access_pattern(key)
            if len(pattern) >= self.warmup_threshold:
                # Calculate average time between accesses
                intervals = [
                    (t2 - t1).total_seconds()
                    for t1, t2 in zip(pattern[:-1], pattern[1:])
                ]
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    last_access = pattern[-1]
                    time_since_last = (datetime.utcnow() - last_access).total_seconds()
                    
                    # If we're approaching the average interval, pre-warm
                    if time_since_last >= avg_interval * 0.8:
                        self._warmup_tasks.add(
                            asyncio.create_task(self._warm_cache(key))
                        )
                        
    async def _warm_cache(self, key: str) -> None:
        """Pre-warm cache for a key."""
        try:
            # Implement your cache warming logic here
            # This might involve fetching fresh data from the database
            self.logger.info(f"Pre-warming cache for key: {key}")
            # await self._fetch_fresh_data(key)
        except Exception as e:
            self.logger.error(f"Error warming cache for {key}: {str(e)}")
        finally:
            # Clean up completed task
            for task in self._warmup_tasks:
                if task.done():
                    self._warmup_tasks.remove(task)
                    
    async def get(
        self,
        key: str,
        default: Any = None,
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache, trying local cache first then Redis."""
        # Try local cache first
        if value := self.local_cache.get(key):
            return value
            
        # Try Redis
        try:
            data = self.redis.get(key)
            if not data:
                return default
                
            entry = CacheEntry.from_dict(json.loads(data))
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
            # Get current version if updating
            current_version = 1
            if version is None:
                data = self.redis.get(key)
                if data:
                    entry = CacheEntry.from_dict(json.loads(data))
                    current_version = entry.version + 1
                    
            # Create new entry
            entry = CacheEntry(
                value=value,
                ttl=ttl,
                version=version or current_version
            )
            
            # Update Redis
            self.redis.setex(
                key,
                ttl,
                json.dumps(entry.to_dict())
            )
            
            # Update local cache
            self.local_cache.put(key, value, ttl)
            
            # Trigger invalidation callbacks with exponential backoff
            await self._trigger_invalidation_with_backoff(key)
            
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
            self.redis.delete(key)
            if key in self.local_cache.cache:
                del self.local_cache.cache[key]
                
            await self._trigger_invalidation_with_backoff(key)
            
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {str(e)}")
            
    async def register_invalidation_callback(
        self,
        key_pattern: str,
        callback: Callable
    ) -> None:
        """Register a callback for cache invalidation events."""
        if key_pattern not in self._invalidation_callbacks:
            self._invalidation_callbacks[key_pattern] = []
        self._invalidation_callbacks[key_pattern].append(callback)
        
    async def _trigger_invalidation_with_backoff(self, key: str) -> None:
        """Trigger invalidation callbacks with exponential backoff."""
        for pattern, callbacks in self._invalidation_callbacks.items():
            if pattern in key:
                for i, callback in enumerate(callbacks):
                    # Add jitter to prevent thundering herd
                    delay = (2 ** i) * (0.1 + random.random() * 0.1)
                    try:
                        await asyncio.sleep(delay)
                        await callback(key)
                    except Exception as e:
                        self.logger.error(
                            f"Error in cache invalidation callback: {str(e)}"
                        )

def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    key_builder: Optional[Callable] = None
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager instance
            # This should be injected in a real application
            cache_manager = CacheManager(Redis())
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                key_parts = [key_prefix, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                
            # Try to get from cache
            result = await cache_manager.get(cache_key)
            if result is not None:
                return result
                
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            return result
            
        return wrapper
    return decorator 