"""API test fixtures."""
import pytest
from fastapi.testclient import TestClient
from typing import Dict, Generator
from unittest.mock import AsyncMock, MagicMock

from src.api.main import app
from src.api.dependencies import (
    get_verified_redis,
    get_verified_event_system,
    get_stripe_client,
    get_db,
    get_security_manager
)
from src.utils.event_system import EventSystem
import stripe
from redis.asyncio import Redis

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock()
    mock.is_connected = True
    mock.connection_state = True
    mock.verify_connection = AsyncMock(return_value=True)
    mock.redis = AsyncMock()
    mock.redis.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    return mock

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client."""
    mock = MagicMock(spec=stripe)
    return mock

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    return mock

@pytest.fixture
def mock_security_manager():
    """Create a mock security manager."""
    mock = AsyncMock()
    mock.verify_api_key = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def test_client(
    mock_event_system,
    mock_stripe,
    mock_db,
    mock_security_manager
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    app.dependency_overrides[get_verified_event_system] = lambda: mock_event_system
    app.dependency_overrides[get_stripe_client] = lambda: mock_stripe
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_security_manager] = lambda: mock_security_manager
    
    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()

@pytest.fixture
def api_key_header() -> Dict[str, str]:
    """Create a test API key header."""
    return {"X-API-Key": "test-api-key"} 