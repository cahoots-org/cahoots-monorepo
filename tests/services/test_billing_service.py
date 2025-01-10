"""Tests for billing service."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.billing import BillingService
from src.database.models import Organization
from src.models.billing import SubscriptionTier, Invoice, UsageRecord
from src.utils.stripe_client import StripeClient

@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    return db

@pytest.fixture
def mock_stripe():
    """Create mock Stripe client."""
    return AsyncMock(spec=StripeClient)

@pytest.fixture
def billing_service(mock_db, mock_stripe):
    """Create billing service instance."""
    return BillingService(mock_db, mock_stripe)

@pytest.fixture
def sample_organization():
    """Create sample organization."""
    return Organization(
        id="org_test",
        name="Test Organization",
        customer_id="cus_test",
        subscription_tier="pro",
        subscription_status="active",
        subscription_id="sub_test",
        subscription_item_id="si_test"
    )

@pytest.fixture
def sample_subscription_tier():
    """Create sample subscription tier."""
    return SubscriptionTier(
        id="pro",
        name="Pro",
        price_monthly=Decimal("29.99"),
        price_yearly=Decimal("299.99"),
        features={
            "api_calls": 100000,
            "storage_gb": 100
        },
        limits={
            "max_users": 10,
            "max_projects": 10
        }
    )

@pytest.mark.asyncio
async def test_create_subscription_success(
    billing_service,
    sample_organization,
    sample_subscription_tier,
    mock_db,
    mock_stripe
):
    """Test successful subscription creation."""
    # Configure mocks
    mock_stripe.create_subscription.return_value = {
        "id": "sub_test",
        "status": "active",
        "current_period_end": 1735689600,  # 2025-01-01
        "items": {
            "data": [{"id": "si_test"}]
        }
    }
    
    mock_db.get.return_value = AsyncMock(
        id=sample_organization.id,
        subscription_tier="free",
        subscription_status="inactive"
    )
    
    # Create subscription
    result = await billing_service.create_subscription(
        organization=sample_organization,
        tier_id="pro",
        payment_method_id="pm_test",
        is_yearly=False
    )
    
    # Verify Stripe API was called
    mock_stripe.create_subscription.assert_called_once_with(
        customer_id=sample_organization.customer_id,
        payment_method_id="pm_test",
        price_id=sample_subscription_tier.price_monthly
    )
    
    # Verify database was updated
    mock_db.commit.assert_called_once()
    
    # Verify response
    assert result["subscription_id"] == "sub_test"
    assert result["status"] == "active"
    assert result["current_period_end"] == 1735689600

@pytest.mark.asyncio
async def test_add_payment_method_success(
    billing_service,
    sample_organization,
    mock_stripe
):
    """Test successful payment method addition."""
    # Configure mock
    mock_stripe.add_payment_method.return_value = {
        "id": "pm_test",
        "type": "card",
        "card": {
            "last4": "4242",
            "brand": "visa"
        }
    }
    
    # Add payment method
    result = await billing_service.add_payment_method(
        organization=sample_organization,
        payment_method_token="tok_test",
        set_default=True
    )
    
    # Verify Stripe API was called
    mock_stripe.add_payment_method.assert_called_once_with(
        customer_id=sample_organization.customer_id,
        payment_method_token="tok_test",
        set_default=True
    )
    
    # Verify response
    assert result["payment_method_id"] == "pm_test"
    assert result["type"] == "card"
    assert result["card"]["last4"] == "4242"

@pytest.mark.asyncio
async def test_list_invoices_success(
    billing_service,
    sample_organization,
    mock_db
):
    """Test successful invoice listing."""
    # Create mock invoice data
    mock_invoices = [
        MagicMock(
            id="inv_test1",
            organization_id=sample_organization.id,
            amount=29.99,
            status="paid",
            due_date=datetime.utcnow(),
            paid_date=datetime.utcnow(),
            line_items=[{"description": "Pro Plan"}],
            created_at=datetime.utcnow()
        ),
        MagicMock(
            id="inv_test2",
            organization_id=sample_organization.id,
            amount=29.99,
            status="pending",
            due_date=datetime.utcnow() + timedelta(days=30),
            paid_date=None,
            line_items=[{"description": "Pro Plan"}],
            created_at=datetime.utcnow()
        )
    ]
    
    # Configure mock database response
    mock_result = AsyncMock()
    mock_scalar = AsyncMock()
    mock_scalar.all = AsyncMock(return_value=mock_invoices)
    mock_result.scalars = AsyncMock(return_value=mock_scalar)
    mock_db.execute.return_value = mock_result

    # List invoices
    invoices = await billing_service.list_invoices(
        organization=sample_organization,
        limit=10
    )

    # Verify results
    assert len(invoices) == 2
    assert invoices[0].id == "inv_test1"
    assert invoices[0].status == "paid"
    assert invoices[1].id == "inv_test2"
    assert invoices[1].status == "pending"

@pytest.mark.asyncio
async def test_get_usage_success(
    billing_service,
    sample_organization,
    mock_db
):
    """Test successful usage retrieval."""
    # Configure test data
    start_time = datetime.utcnow() - timedelta(days=30)
    end_time = datetime.utcnow()

    # Create mock usage records
    mock_records = [
        MagicMock(
            id="ur_test1",
            organization_id=sample_organization.id,
            metric="api_calls",
            quantity=1000,
            timestamp=datetime.utcnow() - timedelta(days=1)
        ),
        MagicMock(
            id="ur_test2",
            organization_id=sample_organization.id,
            metric="api_calls",
            quantity=2000,
            timestamp=datetime.utcnow()
        )
    ]

    # Configure mock database response
    mock_result = AsyncMock()
    mock_scalar = AsyncMock()
    mock_scalar.all = AsyncMock(return_value=mock_records)
    mock_result.scalars = AsyncMock(return_value=mock_scalar)
    mock_db.execute.return_value = mock_result

    # Get usage records
    records = await billing_service.get_usage(
        organization=sample_organization,
        metric="api_calls",
        start_time=start_time,
        end_time=end_time
    )

    # Verify results
    assert len(records) == 2
    assert records[0].id == "ur_test1"
    assert records[0].quantity == 1000
    assert records[1].id == "ur_test2"
    assert records[1].quantity == 2000

@pytest.mark.asyncio
async def test_get_subscription_tier_success(billing_service):
    """Test successful subscription tier retrieval."""
    # Get subscription tier
    tier = await billing_service._get_subscription_tier("pro")
    
    # Verify response
    assert tier.id == "pro"
    assert tier.name == "Pro"
    assert tier.price_monthly == Decimal("29.99")
    assert tier.price_yearly == Decimal("299.99")
    assert tier.features["api_calls"] == 100000
    assert tier.limits["max_users"] == 10

@pytest.mark.asyncio
async def test_get_subscription_tier_not_found(billing_service):
    """Test subscription tier not found."""
    # Get subscription tier
    tier = await billing_service._get_subscription_tier("invalid")
    
    # Verify response
    assert tier is None 