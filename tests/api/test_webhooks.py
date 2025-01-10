"""Tests for webhook endpoints."""
import json
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import stripe
from fastapi import FastAPI, HTTPException
from src.api.webhook import router, stripe_webhook
from src.services.stripe_service import StripeClient

# Sample webhook events for testing
SAMPLE_EVENTS = {
    "subscription_created": {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "org_test",
                "status": "active",
                "plan": {
                    "id": "enterprise_plan"
                }
            }
        }
    },
    "subscription_updated": {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "org_test",
                "status": "active",
                "plan": {
                    "id": "enterprise_plan"
                }
            }
        }
    },
    "subscription_deleted": {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "org_test",
                "status": "canceled"
            }
        }
    },
    "payment_succeeded": {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "inv_test",
                "customer": "org_test",
                "amount_paid": 5000,
                "subscription": "sub_test"
            }
        }
    }
}

@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application.
    
    Returns:
        FastAPI application
    """
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def mock_stripe_client() -> MagicMock:
    """Create mock Stripe client.
    
    Returns:
        Mock Stripe client
    """
    mock = MagicMock(spec=StripeClient)
    return mock

@pytest.fixture
def mock_event_system() -> AsyncMock:
    """Create mock event system.
    
    Returns:
        Mock event system
    """
    mock = AsyncMock()
    mock.publish = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_request() -> MagicMock:
    """Create mock request.
    
    Returns:
        Mock request
    """
    mock = MagicMock()
    mock.headers = {"stripe-signature": "test_signature"}
    return mock

@pytest.mark.asyncio
async def test_webhook_subscription_created(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of subscription created event."""
    event = MagicMock()
    event.type = "customer.subscription.created"
    event.data.object = MagicMock()
    event.data.object.customer = "org_test"
    event.data.object.id = "sub_test"
    event.data.object.status = "active"
    event.data.object.plan.id = "enterprise_plan"

    # Configure mock request
    mock_request.headers = {"stripe-signature": "test_signature"}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["subscription_created"]).encode())
    mock_stripe_client.construct_event.return_value = event

    response = await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)

    assert response.status == "success"
    mock_event_system.publish.assert_called_once_with({
        "type": "subscription_created",
        "payload": {
            "customer_id": "org_test",
            "subscription_id": "sub_test",
            "status": "active",
            "plan": "enterprise_plan"
        }
    })

@pytest.mark.asyncio
async def test_webhook_subscription_updated(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of subscription updated event."""
    event = MagicMock()
    event.type = "customer.subscription.updated"
    event.data.object = MagicMock()
    event.data.object.customer = "org_test"
    event.data.object.id = "sub_test"
    event.data.object.status = "active"
    event.data.object.plan.id = "enterprise_plan"

    # Configure mock request
    mock_request.headers = {"stripe-signature": "test_signature"}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["subscription_updated"]).encode())
    mock_stripe_client.construct_event.return_value = event

    response = await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)

    assert response.status == "success"
    mock_event_system.publish.assert_called_once_with({
        "type": "subscription_updated",
        "payload": {
            "customer_id": "org_test",
            "subscription_id": "sub_test",
            "status": "active",
            "plan": "enterprise_plan"
        }
    })

@pytest.mark.asyncio
async def test_webhook_subscription_deleted(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of subscription deleted event."""
    event = MagicMock()
    event.type = "customer.subscription.deleted"
    event.data.object = MagicMock()
    event.data.object.customer = "org_test"
    event.data.object.id = "sub_test"
    event.data.object.status = "canceled"

    # Configure mock request
    mock_request.headers = {"stripe-signature": "test_signature"}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["subscription_deleted"]).encode())
    mock_stripe_client.construct_event.return_value = event

    response = await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)

    assert response.status == "success"
    mock_event_system.publish.assert_called_once_with({
        "type": "subscription_deleted",
        "payload": {
            "customer_id": "org_test",
            "subscription_id": "sub_test",
            "status": "canceled"
        }
    })

@pytest.mark.asyncio
async def test_webhook_payment_succeeded(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of payment succeeded event."""
    event = MagicMock()
    event.type = "invoice.payment_succeeded"
    event.data.object = MagicMock()
    event.data.object.customer = "org_test"
    event.data.object.id = "inv_test"
    event.data.object.amount_paid = 5000
    event.data.object.subscription = "sub_test"

    # Configure mock request
    mock_request.headers = {"stripe-signature": "test_signature"}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["payment_succeeded"]).encode())
    mock_stripe_client.construct_event.return_value = event

    response = await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)

    assert response.status == "success"
    mock_event_system.publish.assert_called_once_with({
        "type": "payment_succeeded",
        "payload": {
            "customer_id": "org_test",
            "invoice_id": "inv_test",
            "amount_paid": 5000,
            "subscription_id": "sub_test"
        }
    })

@pytest.mark.asyncio
async def test_webhook_missing_signature(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of missing signature header."""
    # Configure mock request with missing signature
    mock_request.headers = {}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["subscription_created"]).encode())

    with pytest.raises(HTTPException) as exc:
        await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)
    assert exc.value.status_code == 400
    assert "Missing stripe-signature header" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_webhook_invalid_signature(
    mock_request: MagicMock,
    mock_event_system: AsyncMock,
    mock_stripe_client: MagicMock
) -> None:
    """Test handling of invalid webhook signature."""
    # Configure mock request with invalid signature
    mock_request.headers = {"stripe-signature": "invalid_signature"}
    mock_request.body = AsyncMock(return_value=json.dumps(SAMPLE_EVENTS["subscription_created"]).encode())
    mock_stripe_client.construct_event.side_effect = ValueError("Invalid signature")

    with pytest.raises(HTTPException) as exc:
        await stripe_webhook(mock_request, mock_event_system, mock_stripe_client)
    assert exc.value.status_code == 400
    assert "Invalid signature" in str(exc.value.detail) 