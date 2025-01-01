"""Integration test fixtures."""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from redis.asyncio import Redis

from src.api.main import app
from src.utils.event_system import EventSystem


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Create a Redis client for testing."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        client_name="ai_dev_team_test"
    )
    try:
        await client.ping()
        print("Connected to Redis 7.4.1 in master mode")
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def event_system(redis_client: Redis) -> AsyncGenerator[EventSystem, None]:
    """Create an event system for testing."""
    system = EventSystem()
    system.redis = redis_client
    system._connected = True
    yield system
    try:
        await system.stop_listening()
    except Exception:
        # Ignore any errors during cleanup
        pass


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client 