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


@pytest_asyncio.fixture
async def redis_client(event_loop: asyncio.AbstractEventLoop) -> AsyncGenerator[Redis, None]:
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


@pytest.fixture
async def event_system(mock_redis):
    """Create event system instance."""
    from src.utils.event_system import EventSystem
    system = EventSystem(redis=mock_redis)
    await system.connect()  # Ensure connection is established
    system._pubsub = await mock_redis.pubsub()  # Initialize pubsub
    await system._pubsub.ping()  # Verify pubsub connection
    return system


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client 


@pytest.fixture
def mock_github_config():
    """Create mock GitHub config."""
    return {
        "token": "mock_token",
        "owner": "test_owner",
        "repo": "test_repo",
        "base_branch": "main"
    } 