"""Test webhook endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import stripe.error

from src.api.webhook import router, WebhookResponse

@pytest.fixture
def mock_event_system():
    """Create a mock event system for testing."""
    mock = AsyncMock()
    mock.is_connected = True
    mock.verify_connection.return_value = True
    mock.disconnect = AsyncMock()
    return mock

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client for testing."""
    mock = MagicMock()
    mock.construct_event = MagicMock()
    mock.handle_webhook_event = AsyncMock()
    return mock

@pytest.fixture
def app(mock_event_system, mock_stripe):
    """Create test FastAPI app with mocked dependencies."""
    app = FastAPI()
    
    # Override dependencies with mocks
    async def get_mock_event_system():
        return mock_event_system
        
    async def get_mock_stripe():
        return mock_stripe
        
    app.dependency_overrides = {
        "get_verified_event_system": get_mock_event_system,
        "get_stripe_client": get_mock_stripe
    }
    app.include_router(router)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

def test_webhook_missing_signature(client):
    """Test webhook fails with missing signature."""
    response = client.post("/webhooks", json={})
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing stripe-signature header"}

def test_webhook_invalid_signature(client, mock_stripe):
    """Test webhook fails with invalid signature."""
    mock_stripe.construct_event.side_effect = stripe.error.SignatureVerificationError(
        "Invalid signature", 
        "sig_header"
    )
    
    response = client.post(
        "/webhooks",
        json={},
        headers={"stripe-signature": "invalid"}
    )
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid signature"}
    mock_stripe.construct_event.assert_called_once()

def test_webhook_success(client, mock_stripe, mock_event_system):
    """Test webhook succeeds with valid signature."""
    mock_event = MagicMock()
    mock_stripe.construct_event.return_value = mock_event
    
    response = client.post(
        "/webhooks",
        json={},
        headers={"stripe-signature": "valid"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify mocks were called correctly
    mock_stripe.construct_event.assert_called_once()
    mock_stripe.handle_webhook_event.assert_called_once_with(mock_event)
    mock_event_system.disconnect.assert_called_once() 