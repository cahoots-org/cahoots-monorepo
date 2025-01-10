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
    get_base_redis,
    get_base_event_system,
    get_session
)
from src.utils.event_system import EventSystem
from src.utils.stripe_client import StripeClient
from redis.asyncio import Redis

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock(spec=Redis)
    mock.ping.return_value = True
    return mock

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    mock = AsyncMock(spec=EventSystem)
    mock.is_connected = True
    mock.verify_connection.return_value = True
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    return mock

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client."""
    mock = MagicMock(spec=StripeClient)
    mock.construct_event = MagicMock()
    mock.handle_webhook_event = AsyncMock()
    return mock

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    return mock

@pytest.fixture
def test_client(
    mock_redis,
    mock_event_system,
    mock_stripe,
    mock_db
) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    app.dependency_overrides = {
        get_base_redis: lambda: mock_redis,
        get_verified_redis: lambda: mock_redis,
        get_base_event_system: lambda: mock_event_system,
        get_verified_event_system: lambda: mock_event_system,
        get_stripe_client: lambda: mock_stripe,
        get_session: lambda: mock_db
    }
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}

@pytest.fixture
def api_key_header() -> Dict[str, str]:
    """Create API key header for authentication."""
    return {"X-API-Key": "test-api-key"} 