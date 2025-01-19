"""Test webhook endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import stripe.error
from fastapi import HTTPException, Request

from src.api.webhook import stripe_webhook

@pytest.fixture
def mock_event_system():
    """Create a mock event system for testing."""
    mock = AsyncMock()
    mock.is_connected = True
    mock.verify_connection.return_value = True
    return mock

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client for testing."""
    mock = MagicMock()
    mock.verify_webhook = MagicMock()
    return mock

@pytest.fixture
def mock_request():
    """Create a mock request."""
    mock = AsyncMock()
    mock.body = AsyncMock(return_value=b'{"test": "data"}')
    mock.headers = {"stripe-signature": "test-sig"}
    return mock

@pytest.mark.asyncio
async def test_webhook_missing_signature(mock_request, mock_event_system, mock_stripe):
    """Test webhook fails with missing signature."""
    mock_request.headers = {}
    
    with pytest.raises(HTTPException) as exc:
        await stripe_webhook(mock_request, mock_event_system, mock_stripe)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_webhook_invalid_signature(mock_request, mock_event_system, mock_stripe):
    """Test webhook fails with invalid signature."""
    mock_stripe.verify_webhook.side_effect = Exception("Invalid signature")
    
    with pytest.raises(HTTPException) as exc:
        await stripe_webhook(mock_request, mock_event_system, mock_stripe)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_webhook_success(mock_request, mock_event_system, mock_stripe):
    """Test webhook succeeds with valid signature."""
    mock_event = MagicMock()
    mock_event.type = "test.event"
    mock_event.id = "evt_123"
    mock_event.data.object = {"foo": "bar"}
    mock_stripe.verify_webhook.return_value = mock_event
    
    response = await stripe_webhook(mock_request, mock_event_system, mock_stripe)
    
    assert response.status == "success"
    mock_stripe.verify_webhook.assert_called_once_with(b'{"test": "data"}', "test-sig")
    mock_event_system.publish.assert_called_once_with("stripe.webhook", {
        "event_type": "test.event",
        "event_id": "evt_123",
        "data": {"foo": "bar"}
    }) 