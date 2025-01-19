"""Integration tests for rate limiting."""
import pytest
import asyncio
from fastapi import HTTPException
import time
from unittest.mock import AsyncMock

from src.utils.security import RateLimiter
from src.core.config import SecurityConfig

@pytest.mark.asyncio
async def test_basic_rate_limiting(redis_client):
    """Test basic rate limiting behavior."""
    # Given a rate limiter with a small window
    limiter = RateLimiter(redis=redis_client)
    key = "test:basic"
    limit = 3
    window = 2

    # When making requests within the limit
    results = []
    for _ in range(limit):
        results.append(await limiter.check_rate_limit(key, limit, window))

    # Then all requests should succeed
    assert all(results), "All requests within limit should succeed"

    # When exceeding the limit
    exceeded = await limiter.check_rate_limit(key, limit, window)

    # Then it should be blocked
    assert not exceeded, "Request exceeding limit should be blocked"

@pytest.mark.asyncio
async def test_window_reset(redis_client):
    """Test rate limit window reset behavior."""
    # Given a rate limiter with a very short window
    limiter = RateLimiter(redis=redis_client)
    key = "test:window"
    limit = 2
    window = 1

    # When using all requests
    for _ in range(limit):
        await limiter.check_rate_limit(key, limit, window)

    # And waiting for window reset
    await asyncio.sleep(window + 0.1)

    # Then new requests should succeed
    result = await limiter.check_rate_limit(key, limit, window)
    assert result, "Request after window reset should succeed"

@pytest.mark.asyncio
async def test_multiple_keys(redis_client):
    """Test rate limiting for different keys."""
    # Given a rate limiter
    limiter = RateLimiter(redis=redis_client)
    limit = 2
    window = 5

    # When using different keys
    key1_results = []
    key2_results = []
    
    # Then each key should have its own limit
    for _ in range(limit):
        key1_results.append(await limiter.check_rate_limit("test:key1", limit, window))
        key2_results.append(await limiter.check_rate_limit("test:key2", limit, window))

    assert all(key1_results), "All requests for key1 should succeed"
    assert all(key2_results), "All requests for key2 should succeed"

    # When exceeding limit for key1
    key1_exceeded = await limiter.check_rate_limit("test:key1", limit, window)
    key2_additional = await limiter.check_rate_limit("test:key2", limit, window)

    # Then key1 should be blocked but key2 should still work
    assert not key1_exceeded, "Key1 should be rate limited"
    assert key2_additional, "Key2 should still allow requests"

@pytest.mark.asyncio
async def test_limit_info(redis_client):
    """Test rate limit information retrieval."""
    # Given a rate limiter
    limiter = RateLimiter(redis=redis_client)
    key = "test:info"
    limit = 5
    window = 10

    # When making some requests
    for _ in range(3):
        await limiter.check_rate_limit(key, limit, window)

    # Then limit info should be accurate
    info = await limiter.get_limit_info(key, limit, window)
    assert info["limit"] == limit, "Should return correct limit"
    assert info["remaining"] == 2, "Should have 2 requests remaining"
    assert "reset_at" in info, "Should include reset timestamp" 

@pytest.mark.asyncio
async def test_concurrent_requests(redis_client):
    """Test rate limiting under concurrent load."""
    # Given a rate limiter with strict limits
    limiter = RateLimiter(redis=redis_client)
    key = "test:concurrent"
    limit = 5
    window = 2

    # When making concurrent requests
    async def make_request():
        return await limiter.check_rate_limit(key, limit, window)

    # Create many concurrent requests
    tasks = [make_request() for _ in range(limit * 2)]
    results = await asyncio.gather(*tasks)

    # Then only the limit number should succeed
    assert sum(results) == limit, f"Expected {limit} successful requests, got {sum(results)}"

    # And subsequent requests should be blocked
    blocked = await limiter.check_rate_limit(key, limit, window)
    assert not blocked, "Additional requests should be blocked" 

@pytest.mark.asyncio
async def test_redis_failure_recovery(redis_client):
    """Test rate limiter behavior during Redis failures."""
    # Given a rate limiter
    limiter = RateLimiter(redis=redis_client)
    key = "test:failure"
    limit = 3
    window = 2

    # When Redis is working
    initial_result = await limiter.check_rate_limit(key, limit, window)
    assert initial_result, "First request should succeed"

    # When Redis fails
    redis_client.get = AsyncMock(side_effect=Exception("Redis connection error"))
    redis_client.pipeline = AsyncMock(side_effect=Exception("Redis connection error"))

    # Then requests should be allowed (fail open)
    failure_result = await limiter.check_rate_limit(key, limit, window)
    assert failure_result, "Should fail open on Redis errors"

    # When Redis recovers
    redis_client.get = AsyncMock(return_value=None)
    redis_client.pipeline = AsyncMock()
    pipeline = AsyncMock()
    pipeline.get = AsyncMock(return_value=None)
    pipeline.ttl = AsyncMock(return_value=-1)
    pipeline.incr = AsyncMock(return_value=1)
    pipeline.expire = AsyncMock(return_value=True)
    pipeline.execute = AsyncMock(return_value=[None, -1, 1, True])
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock()
    redis_client.pipeline.return_value = pipeline

    # Then rate limiting should resume
    recovery_result = await limiter.check_rate_limit(key, limit, window)
    assert recovery_result, "Should resume rate limiting after recovery" 