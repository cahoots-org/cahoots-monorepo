"""Billing service tests."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from cahoots_service.services.billing import BillingService
from cahoots_core.models.db_models import Organization
from cahoots_core.models.billing import SubscriptionTier, Invoice, UsageRecord
from cahoots_core.utils.infrastructure import StripeClient
from cahoots_core.utils.dependencies import ServiceDeps

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.db = AsyncMock(spec=AsyncSession)
    deps.db.commit = AsyncMock()
    deps.db.rollback = AsyncMock()
    deps.db.close = AsyncMock()
    deps.stripe = AsyncMock(spec=StripeClient)
    return deps

@pytest.fixture
def billing_service(mock_deps):
    """Create billing service instance."""
    return BillingService(deps=mock_deps)

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
    mock_deps
):
    """Test successful subscription creation."""
    # Configure mocks
    mock_deps.stripe.create_subscription.return_value = {
        "id": "sub_test",
        "status": "active",
        "current_period_end": 1735689600,  # 2025-01-01
        "items": {
            "data": [{"id": "si_test"}]
        }
    }
    
    mock_deps.db.get.return_value = AsyncMock(
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
    mock_deps.stripe.create_subscription.assert_called_once_with(
        customer_id=sample_organization.customer_id,
        payment_method_id="pm_test",
        price_id=sample_subscription_tier.price_monthly
    )
    
    # Verify database was updated
    mock_deps.db.commit.assert_called_once()
    
    # Verify response
    assert result["subscription_id"] == "sub_test"
    assert result["status"] == "active"
    assert result["current_period_end"] == 1735689600

@pytest.mark.asyncio
async def test_add_payment_method_success(
    billing_service,
    sample_organization,
    mock_deps
):
    """Test successful payment method addition."""
    # Configure mock
    mock_deps.stripe.add_payment_method.return_value = {
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
    mock_deps.stripe.add_payment_method.assert_called_once_with(
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
    mock_deps
):
    """Test successful invoice listing."""
    # Create mock invoice data
    mock_invoices = [
        MagicMock(
            id="inv_test1",
            organization_id=sample_organization.id,
            customer_id="cus_test1",
            subscription_id="sub_test1",
            amount_due=2999,
            status="paid",
            created=datetime.utcnow()
        ),
        MagicMock(
            id="inv_test2",
            organization_id=sample_organization.id,
            customer_id="cus_test2",
            subscription_id="sub_test2",
            amount_due=2999,
            status="pending",
            created=datetime.utcnow()
        )
    ]
    
    # Configure mock database response
    mock_result = AsyncMock()
    mock_scalar = AsyncMock()
    mock_scalar.all = AsyncMock(return_value=mock_invoices)
    mock_result.scalars = AsyncMock(return_value=mock_scalar)
    mock_deps.db.execute.return_value = mock_result

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
    mock_deps
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
    mock_deps.db.execute.return_value = mock_result

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