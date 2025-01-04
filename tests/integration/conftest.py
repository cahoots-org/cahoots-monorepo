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


@pytest_asyncio.fixture
async def event_system(redis_client: Redis) -> AsyncGenerator[EventSystem, None]:
    """Create an event system for testing."""
    from src.api.core import get_event_system, _event_system
    
    # Store original event system if it exists
    original_event_system = _event_system
    
    # Create test event system
    system = EventSystem()
    await system.connect(redis_client)
    
    # Replace global event system
    import src.api.core
    src.api.core._event_system = system
    
    yield system
    
    try:
        await system.stop_listening()
    except Exception:
        # Ignore any errors during cleanup
        pass
        
    # Restore original event system
    src.api.core._event_system = original_event_system


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client 