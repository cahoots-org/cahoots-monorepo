"""Test billing endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import stripe
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.billing import (
    get_subscription,
    create_subscription,
    update_subscription,
    cancel_subscription,
    get_payment_methods,
    add_payment_method,
    remove_payment_method,
    get_invoices,
    get_invoice,
    pay_invoice,
    get_usage,
    get_billing_portal
)
from src.schemas.billing import (
    SubscriptionResponse,
    PaymentMethodResponse,
    InvoiceResponse,
    UsageResponse,
    BillingPortalResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    PaymentMethodCreate
)

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    stripe_mock = MagicMock()
    stripe_mock.error = stripe.error
    return {
        "db": AsyncMock(spec=AsyncSession),
        "stripe": stripe_mock,
        "event_system": AsyncMock()
    }

@pytest.mark.asyncio
async def test_get_subscription(mock_deps):
    """Test getting a subscription returns expected data."""
    expected_subscription = SubscriptionResponse(
        id="sub_test",
        customer_id="cus_test",
        price_id="plan_test",
        status="active",
        current_period_end="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].get_subscription = AsyncMock(return_value=expected_subscription.model_dump())

    result = await get_subscription(
        subscription_id="sub_test",
        **mock_deps
    )
    assert result == expected_subscription

@pytest.mark.asyncio
async def test_create_subscription(mock_deps):
    """Test creating a subscription with valid data succeeds."""
    expected_subscription = SubscriptionResponse(
        id="sub_test",
        customer_id="cus_test",
        price_id="plan_test",
        status="active",
        current_period_end="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].create_subscription = AsyncMock(return_value=expected_subscription.model_dump())

    data = SubscriptionCreate(
        customer_id="cus_test",
        price_id="plan_test",
        payment_method_id="pm_test"
    )
    result = await create_subscription(data=data, **mock_deps)
    assert result == expected_subscription

@pytest.mark.asyncio
async def test_update_subscription(mock_deps):
    """Test updating a subscription with new price."""
    expected_subscription = SubscriptionResponse(
        id="sub_test",
        customer_id="cus_test",
        price_id="plan_test_new",
        status="active",
        current_period_end="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].update_subscription = AsyncMock(return_value=expected_subscription.model_dump())

    data = SubscriptionUpdate(price_id="plan_test_new")
    result = await update_subscription(
        subscription_id="sub_test",
        data=data,
        **mock_deps
    )
    assert result == expected_subscription

@pytest.mark.asyncio
async def test_cancel_subscription(mock_deps):
    """Test canceling a subscription changes status to canceled."""
    expected_subscription = SubscriptionResponse(
        id="sub_test",
        customer_id="cus_test",
        price_id="plan_test",
        status="canceled",
        current_period_end="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].cancel_subscription = AsyncMock(return_value=expected_subscription.model_dump())

    result = await cancel_subscription(
        subscription_id="sub_test",
        **mock_deps
    )
    assert result == expected_subscription
    assert result.status == "canceled"

@pytest.mark.asyncio
async def test_get_payment_methods(mock_deps):
    """Test retrieving payment methods returns list of methods."""
    expected_methods = [
        PaymentMethodResponse(
            id="pm_test",
            type="card",
            card={
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2024
            }
        )
    ]
    mock_deps["stripe"].list_payment_methods = AsyncMock(return_value=[m.model_dump() for m in expected_methods])

    result = await get_payment_methods(
        customer_id="cus_test",
        **mock_deps
    )
    assert result == expected_methods
    assert len(result) == 1
    assert result[0].type == "card"

@pytest.mark.asyncio
async def test_add_payment_method(mock_deps):
    """Test adding a new payment method."""
    expected_method = PaymentMethodResponse(
        id="pm_test",
        type="card",
        card={
            "brand": "visa",
            "last4": "4242",
            "exp_month": 12,
            "exp_year": 2024
        }
    )
    mock_deps["stripe"].attach_payment_method = AsyncMock(return_value=expected_method.model_dump())

    data = PaymentMethodCreate(
        payment_method_id="pm_test",
        customer_id="cus_test"
    )
    result = await add_payment_method(data=data, **mock_deps)
    assert result == expected_method
    assert result.type == "card"

@pytest.mark.asyncio
async def test_remove_payment_method(mock_deps):
    """Test removing a payment method."""
    mock_deps["stripe"].detach_payment_method = AsyncMock(return_value=True)

    result = await remove_payment_method(
        payment_method_id="pm_test",
        **mock_deps
    )
    assert result is True

@pytest.mark.asyncio
async def test_get_invoices(mock_deps):
    """Test retrieving customer invoices returns list of invoices."""
    expected_invoices = [
        InvoiceResponse(
            id="inv_test",
            customer_id="cus_test",
            subscription_id="sub_test",
            amount_due=2999,
            status="paid",
            created="2024-01-01T00:00:00Z"
        )
    ]
    mock_deps["stripe"].list_invoices = AsyncMock(return_value=[i.model_dump() for i in expected_invoices])

    result = await get_invoices(
        customer_id="cus_test",
        **mock_deps
    )
    assert result == expected_invoices
    assert len(result) == 1
    assert result[0].status == "paid"

@pytest.mark.asyncio
async def test_get_invoice(mock_deps):
    """Test retrieving a specific invoice."""
    expected_invoice = InvoiceResponse(
        id="inv_test",
        customer_id="cus_test",
        subscription_id="sub_test",
        amount_due=2999,
        status="paid",
        created="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].get_invoice = AsyncMock(return_value=expected_invoice.model_dump())

    result = await get_invoice(
        invoice_id="inv_test",
        **mock_deps
    )
    assert result == expected_invoice
    assert result.status == "paid"

@pytest.mark.asyncio
async def test_pay_invoice(mock_deps):
    """Test paying an invoice changes status to paid."""
    expected_invoice = InvoiceResponse(
        id="inv_test",
        customer_id="cus_test",
        subscription_id="sub_test",
        amount_due=2999,
        status="paid",
        created="2024-01-01T00:00:00Z"
    )
    mock_deps["stripe"].pay_invoice = AsyncMock(return_value=expected_invoice.model_dump())

    result = await pay_invoice(
        invoice_id="inv_test",
        **mock_deps
    )
    assert result == expected_invoice
    assert result.status == "paid"

@pytest.mark.asyncio
async def test_get_usage(mock_deps):
    """Test retrieving subscription usage details."""
    expected_usage = UsageResponse(
        subscription_id="sub_test",
        current_usage=1000,
        limit=10000,
        period_start="2024-01-01T00:00:00Z",
        period_end="2024-02-01T00:00:00Z"
    )
    mock_deps["stripe"].get_subscription_usage = AsyncMock(return_value=expected_usage.model_dump())

    result = await get_usage(
        subscription_id="sub_test",
        **mock_deps
    )
    assert result == expected_usage
    assert result.current_usage < result.limit

@pytest.mark.asyncio
async def test_get_billing_portal(mock_deps):
    """Test generating billing portal URL."""
    expected_portal = BillingPortalResponse(
        url="https://billing.stripe.com/portal/test"
    )
    mock_deps["stripe"].create_billing_portal = AsyncMock(return_value=expected_portal.model_dump())

    result = await get_billing_portal(
        customer_id="cus_test",
        return_url="https://example.com",
        **mock_deps
    )
    assert result == expected_portal
    assert result.url.startswith("https://billing.stripe.com/portal/")

@pytest.mark.asyncio
async def test_subscription_error_handling(mock_deps):
    """Test error handling for subscription operations."""
    error = stripe.error.StripeError("Subscription not found")
    mock_deps["stripe"].get_subscription = AsyncMock(side_effect=error)
    
    with pytest.raises(stripe.error.StripeError) as exc_info:
        await get_subscription("non_existent", **mock_deps)
    assert "Subscription not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_invoice_payment_failure(mock_deps):
    """Test handling failed invoice payment."""
    error = stripe.error.CardError(
        message="Your card was declined",
        param=None,
        code="card_declined",
        http_status=402,
        json_body=None,
        headers=None
    )
    mock_deps["stripe"].pay_invoice = AsyncMock(side_effect=error)
    
    with pytest.raises(stripe.error.CardError) as exc_info:
        await pay_invoice("inv_test", **mock_deps)
    assert "Your card was declined" in str(exc_info.value) 