"""Unit tests for Stripe client module."""
import pytest
from unittest.mock import Mock, patch
from stripe.error import StripeError

from .client import (
    StripeClient,
    StripeClientError,
    PaymentError,
    SubscriptionError,
    CustomerError,
    get_stripe_client
)

@pytest.fixture
def mock_stripe():
    """Mock Stripe API."""
    with patch("stripe.Customer") as mock_customer, \
         patch("stripe.PaymentMethod") as mock_payment_method, \
         patch("stripe.Subscription") as mock_subscription:
             
        yield {
            "customer": mock_customer,
            "payment_method": mock_payment_method,
            "subscription": mock_subscription
        }

@pytest.fixture
def stripe_client():
    """Create a StripeClient instance."""
    return StripeClient("test_key")

@pytest.mark.asyncio
async def test_create_customer_success(stripe_client, mock_stripe):
    """Test successful customer creation."""
    mock_customer = Mock()
    mock_customer.id = "cus_123"
    mock_stripe["customer"].create.return_value = mock_customer
    
    customer = await stripe_client.create_customer(
        email="test@example.com",
        name="Test User",
        description="Test customer",
        metadata={"key": "value"}
    )
    
    assert customer.id == "cus_123"
    mock_stripe["customer"].create.assert_called_once_with(
        email="test@example.com",
        name="Test User",
        description="Test customer",
        metadata={"key": "value"}
    )

@pytest.mark.asyncio
async def test_create_customer_failure(stripe_client, mock_stripe):
    """Test failed customer creation."""
    mock_stripe["customer"].create.side_effect = StripeError("Creation failed")
    
    with pytest.raises(CustomerError, match="Failed to create customer"):
        await stripe_client.create_customer("test@example.com")

@pytest.mark.asyncio
async def test_get_customer_success(stripe_client, mock_stripe):
    """Test successful customer retrieval."""
    mock_customer = Mock()
    mock_customer.id = "cus_123"
    mock_stripe["customer"].retrieve.return_value = mock_customer
    
    customer = await stripe_client.get_customer("cus_123")
    
    assert customer.id == "cus_123"
    mock_stripe["customer"].retrieve.assert_called_once_with("cus_123")

@pytest.mark.asyncio
async def test_get_customer_failure(stripe_client, mock_stripe):
    """Test failed customer retrieval."""
    mock_stripe["customer"].retrieve.side_effect = StripeError("Retrieval failed")
    
    with pytest.raises(CustomerError, match="Failed to get customer"):
        await stripe_client.get_customer("cus_123")

@pytest.mark.asyncio
async def test_update_customer_success(stripe_client, mock_stripe):
    """Test successful customer update."""
    mock_customer = Mock()
    mock_customer.id = "cus_123"
    mock_stripe["customer"].modify.return_value = mock_customer
    
    customer = await stripe_client.update_customer(
        "cus_123",
        email="new@example.com",
        name="New Name"
    )
    
    assert customer.id == "cus_123"
    mock_stripe["customer"].modify.assert_called_once_with(
        "cus_123",
        email="new@example.com",
        name="New Name"
    )

@pytest.mark.asyncio
async def test_update_customer_failure(stripe_client, mock_stripe):
    """Test failed customer update."""
    mock_stripe["customer"].modify.side_effect = StripeError("Update failed")
    
    with pytest.raises(CustomerError, match="Failed to update customer"):
        await stripe_client.update_customer("cus_123")

@pytest.mark.asyncio
async def test_delete_customer_success(stripe_client, mock_stripe):
    """Test successful customer deletion."""
    mock_deleted = Mock()
    mock_deleted.deleted = True
    mock_stripe["customer"].delete.return_value = mock_deleted
    
    result = await stripe_client.delete_customer("cus_123")
    
    assert result is True
    mock_stripe["customer"].delete.assert_called_once_with("cus_123")

@pytest.mark.asyncio
async def test_delete_customer_failure(stripe_client, mock_stripe):
    """Test failed customer deletion."""
    mock_stripe["customer"].delete.side_effect = StripeError("Deletion failed")
    
    with pytest.raises(CustomerError, match="Failed to delete customer"):
        await stripe_client.delete_customer("cus_123")

@pytest.mark.asyncio
async def test_create_payment_method_success(stripe_client, mock_stripe):
    """Test successful payment method creation."""
    mock_payment_method = Mock()
    mock_payment_method.id = "pm_123"
    mock_stripe["payment_method"].create.return_value = mock_payment_method
    mock_stripe["payment_method"].attach.return_value = mock_payment_method
    
    payment_method = await stripe_client.create_payment_method(
        customer_id="cus_123",
        card_number="4242424242424242",
        exp_month=12,
        exp_year=2025,
        cvc="123"
    )
    
    assert payment_method.id == "pm_123"
    mock_stripe["payment_method"].create.assert_called_once_with(
        type="card",
        card={
            "number": "4242424242424242",
            "exp_month": 12,
            "exp_year": 2025,
            "cvc": "123"
        }
    )
    mock_stripe["payment_method"].attach.assert_called_once_with(
        "pm_123",
        customer="cus_123"
    )

@pytest.mark.asyncio
async def test_create_payment_method_failure(stripe_client, mock_stripe):
    """Test failed payment method creation."""
    mock_stripe["payment_method"].create.side_effect = StripeError("Creation failed")
    
    with pytest.raises(PaymentError, match="Failed to create payment method"):
        await stripe_client.create_payment_method(
            "cus_123",
            "4242424242424242",
            12,
            2025,
            "123"
        )

@pytest.mark.asyncio
async def test_create_subscription_success(stripe_client, mock_stripe):
    """Test successful subscription creation."""
    mock_subscription = Mock()
    mock_subscription.id = "sub_123"
    mock_stripe["subscription"].create.return_value = mock_subscription
    
    subscription = await stripe_client.create_subscription(
        customer_id="cus_123",
        price_id="price_123",
        payment_method_id="pm_123",
        trial_days=14,
        metadata={"key": "value"}
    )
    
    assert subscription.id == "sub_123"
    mock_stripe["subscription"].create.assert_called_once_with(
        customer="cus_123",
        items=[{"price": "price_123"}],
        default_payment_method="pm_123",
        trial_period_days=14,
        metadata={"key": "value"}
    )

@pytest.mark.asyncio
async def test_create_subscription_failure(stripe_client, mock_stripe):
    """Test failed subscription creation."""
    mock_stripe["subscription"].create.side_effect = StripeError("Creation failed")
    
    with pytest.raises(SubscriptionError, match="Failed to create subscription"):
        await stripe_client.create_subscription("cus_123", "price_123")

@pytest.mark.asyncio
async def test_cancel_subscription_success(stripe_client, mock_stripe):
    """Test successful subscription cancellation."""
    mock_subscription = Mock()
    mock_subscription.id = "sub_123"
    mock_stripe["subscription"].modify.return_value = mock_subscription
    mock_stripe["subscription"].delete.return_value = mock_subscription
    
    subscription = await stripe_client.cancel_subscription("sub_123")
    
    assert subscription.id == "sub_123"
    mock_stripe["subscription"].modify.assert_called_once_with(
        "sub_123",
        cancel_at_period_end=False
    )
    mock_stripe["subscription"].delete.assert_called_once_with("sub_123")

@pytest.mark.asyncio
async def test_cancel_subscription_failure(stripe_client, mock_stripe):
    """Test failed subscription cancellation."""
    mock_stripe["subscription"].modify.side_effect = StripeError("Cancellation failed")
    
    with pytest.raises(SubscriptionError, match="Failed to cancel subscription"):
        await stripe_client.cancel_subscription("sub_123")

@pytest.mark.asyncio
async def test_get_subscription_success(stripe_client, mock_stripe):
    """Test successful subscription retrieval."""
    mock_subscription = Mock()
    mock_subscription.id = "sub_123"
    mock_stripe["subscription"].retrieve.return_value = mock_subscription
    
    subscription = await stripe_client.get_subscription("sub_123")
    
    assert subscription.id == "sub_123"
    mock_stripe["subscription"].retrieve.assert_called_once_with("sub_123")

@pytest.mark.asyncio
async def test_get_subscription_failure(stripe_client, mock_stripe):
    """Test failed subscription retrieval."""
    mock_stripe["subscription"].retrieve.side_effect = StripeError("Retrieval failed")
    
    with pytest.raises(SubscriptionError, match="Failed to get subscription"):
        await stripe_client.get_subscription("sub_123")

@pytest.mark.asyncio
async def test_list_subscriptions_success(stripe_client, mock_stripe):
    """Test successful subscription listing."""
    mock_subscription = Mock()
    mock_subscription.id = "sub_123"
    mock_list = Mock()
    mock_list.data = [mock_subscription]
    mock_stripe["subscription"].list.return_value = mock_list
    
    subscriptions = await stripe_client.list_subscriptions(
        customer_id="cus_123",
        status="active",
        limit=5
    )
    
    assert len(subscriptions) == 1
    assert subscriptions[0].id == "sub_123"
    mock_stripe["subscription"].list.assert_called_once_with(
        customer="cus_123",
        status="active",
        limit=5
    )

@pytest.mark.asyncio
async def test_list_subscriptions_failure(stripe_client, mock_stripe):
    """Test failed subscription listing."""
    mock_stripe["subscription"].list.side_effect = StripeError("Listing failed")
    
    with pytest.raises(SubscriptionError, match="Failed to list subscriptions"):
        await stripe_client.list_subscriptions()

def test_get_stripe_client():
    """Test global client instance creation."""
    with patch("packages.core.src.utils.infrastructure.stripe.client.StripeClient") as mock_client:
        client1 = get_stripe_client("test_key")
        client2 = get_stripe_client("test_key")
        
        # Should create only one instance
        mock_client.assert_called_once_with("test_key")
        assert client1 == client2 