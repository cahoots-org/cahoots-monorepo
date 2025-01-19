"""Integration test fixtures."""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
import redis.asyncio as redis

from src.api.main import app
from src.utils.event_system import EventSystem
from src.utils.security import SecurityManager, RoleManager, PolicyManager
from src.core.config import SecurityConfig


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.Redis(host='localhost', port=6379, db=0)
    yield client
    await client.aclose()


@pytest.fixture
async def event_system(redis_client):
    """Create event system instance."""
    system = EventSystem(redis_client)
    await system.connect()
    yield system
    await system.disconnect()


@pytest.fixture
def security_config():
    """Create security config for testing."""
    return SecurityConfig(
        jwt_secret="test_secret",
        jwt_algorithm="HS256",
        token_expire_minutes=30
    )


@pytest.fixture
async def role_manager(redis_client):
    """Create role manager instance for testing."""
    manager = RoleManager(redis=redis_client)
    yield manager
    # Clean up any test roles
    await redis_client.flushdb()


@pytest.fixture
async def policy_manager(redis_client):
    """Create a policy manager for testing."""
    manager = PolicyManager(redis=redis_client)
    yield manager
    # Cleanup
    await redis_client.flushdb()


@pytest.fixture
async def security_manager(redis_client, security_config, role_manager):
    """Create security manager instance."""
    manager = SecurityManager(redis=redis_client, config=security_config)
    manager.role_manager = role_manager
    
    # Store test API key
    test_key = "test_api_key"
    await manager.key_manager.store_api_key(
        api_key=test_key,
        organization_id="test-org",
        scopes=["read", "write"],
        expires_in_days=1
    )
    
    # Verify key was stored
    key_data = await manager.key_manager.validate_api_key(test_key)
    if not key_data:
        raise RuntimeError("Failed to store test API key")
        
    # Inject manager into app state
    app.state.security_manager = manager
    return manager


@pytest_asyncio.fixture
async def async_client(security_manager) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    # Inject security manager into middleware
    from src.api.middleware.security import SecurityMiddleware
    for middleware in app.user_middleware:
        if isinstance(middleware.cls, SecurityMiddleware):
            middleware.cls.security_manager = security_manager
            # Also set it on the instance
            if hasattr(middleware, 'instance'):
                middleware.instance.security_manager = security_manager
            break
            
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