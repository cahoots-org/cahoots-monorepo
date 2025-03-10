"""Billing service."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict, cast
from uuid import UUID

from api.dependencies import ServiceDeps
from sqlalchemy import select
from utils.config import ServiceConfig

from cahoots_core.exceptions.api import APIError
from cahoots_core.exceptions.domain import DomainError
from cahoots_core.exceptions.infrastructure import InfrastructureError
from cahoots_core.models.billing import (
    BillingInfo,
    PaymentMethod,
    PaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)
from cahoots_core.models.db_models import (
    Invoice,
    Organization,
    Subscription,
    UsageRecord,
)
from cahoots_core.utils.infrastructure.stripe.client import StripeClient

logger = logging.getLogger(__name__)


class StripeSubscriptionItem(TypedDict):
    id: str
    price: Dict[str, Any]


class StripeSubscriptionData(TypedDict):
    data: List[StripeSubscriptionItem]


class StripeSubscription(TypedDict):
    id: str
    status: str
    current_period_end: int
    items: StripeSubscriptionData


class BillingService:
    """Service for managing billing and subscriptions."""

    def __init__(self, deps: ServiceConfig):
        """Initialize billing service.

        Args:
            deps: Service dependencies
        """
        self.deps = deps

    async def create_subscription(
        self,
        organization: Organization,
        tier_id: str,
        payment_method_id: str,
        is_yearly: bool = False,
    ) -> Dict[str, Any]:
        """Create a new subscription.

        Args:
            organization: Organization to create subscription for
            tier_id: Subscription tier ID
            payment_method_id: Payment method ID
            is_yearly: Whether to bill yearly

        Returns:
            Dict containing subscription details

        Raises:
            ValueError: If tier or payment method is invalid
            stripe.error.StripeError: For Stripe API errors
        """
        # Get subscription tier
        tier = await self._get_subscription_tier(tier_id)
        if not tier:
            raise ValueError(f"Invalid subscription tier: {tier_id}")

        # Create Stripe subscription
        subscription = cast(
            StripeSubscription,
            await self.stripe.create_subscription(
                customer_id=organization.customer_id,
                payment_method_id=payment_method_id,
                price_id=tier.price_yearly if is_yearly else tier.price_monthly,
            ),
        )

        # Update organization subscription
        organization_model = await self.db.get(Organization, organization.id)
        if organization_model:
            organization_model.subscription_tier = tier_id
            organization_model.subscription_status = subscription["status"]
            organization_model.subscription_id = subscription["id"]

            # Safely get subscription item ID
            items = subscription["items"]["data"]
            organization_model.subscription_item_id = items[0]["id"] if items else "unknown"

            await self.db.commit()

        return {
            "subscription_id": subscription["id"],
            "status": subscription["status"],
            "current_period_end": subscription["current_period_end"],
        }

    async def add_payment_method(
        self, organization: Organization, payment_method_token: str, set_default: bool = True
    ) -> Dict[str, Any]:
        """Add a payment method to organization.

        Args:
            organization: Organization to add payment method to
            payment_method_token: Payment method token
            set_default: Whether to set as default payment method

        Returns:
            Dict containing payment method details

        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        # Add payment method in Stripe
        payment_method = await self.stripe.add_payment_method(
            customer_id=organization.customer_id,
            payment_method_token=payment_method_token,
            set_default=set_default,
        )

        return {
            "payment_method_id": payment_method.get("id", "unknown"),
            "type": payment_method.get("type", "unknown"),
            "card": payment_method.get("card", {}),
        }

    async def list_invoices(self, organization: Organization, limit: int = 10) -> List[Invoice]:
        """List organization invoices."""
        # Build query
        query = (
            select(Invoice)
            .where(Invoice.organization_id == organization.id)
            .order_by(Invoice.created.desc())
            .limit(limit)
        )

        # Execute query
        result = await self.db.execute(query)
        result_scalar = await result.scalars()
        invoice_models = await result_scalar.all()

        # Convert to domain models
        return [
            Invoice(
                id=str(invoice.id),
                customer_id=str(invoice.customer_id),
                subscription_id=str(invoice.subscription_id),
                amount_due=invoice.amount_due,
                status=invoice.status,
                created=invoice.created.isoformat(),
            )
            for invoice in invoice_models
        ]

    async def get_usage(
        self,
        organization: Organization,
        metric: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """Get organization usage records."""
        # Build base query
        query = select(UsageRecord).where(
            UsageRecord.organization_id == organization.id, UsageRecord.metric == metric
        )

        # Add time filters
        if start_time:
            query = query.where(UsageRecord.timestamp >= start_time)
        if end_time:
            query = query.where(UsageRecord.timestamp <= end_time)

        # Add ordering
        query = query.order_by(UsageRecord.timestamp.desc())

        # Execute query
        result = await self.db.execute(query)
        result_scalar = await result.scalars()
        record_models = await result_scalar.all()

        # Convert to domain models
        return [
            UsageRecord(
                id=str(record.id),
                organization_id=str(record.organization_id),
                metric=record.metric,
                quantity=record.quantity,
                timestamp=record.timestamp,
            )
            for record in record_models
        ]

    async def _get_subscription_tier(self, tier_id: str) -> Optional[SubscriptionTier]:
        """Get subscription tier by ID.

        Args:
            tier_id: Tier ID to get

        Returns:
            Subscription tier if found, None otherwise
        """
        # TODO: Get from database or config
        tiers = {
            "free": SubscriptionTier(
                id="free",
                name="Free",
                price_monthly=Decimal("0"),
                price_yearly=Decimal("0"),
                features={"api_calls": 1000, "storage_gb": 1},
                limits={"max_users": 1, "max_projects": 1},
            ),
            "pro": SubscriptionTier(
                id="pro",
                name="Pro",
                price_monthly=Decimal("29.99"),
                price_yearly=Decimal("299.99"),
                features={"api_calls": 100000, "storage_gb": 100},
                limits={"max_users": 10, "max_projects": 10},
            ),
            "enterprise": SubscriptionTier(
                id="enterprise",
                name="Enterprise",
                price_monthly=Decimal("299.99"),
                price_yearly=Decimal("2999.99"),
                features={"api_calls": -1, "storage_gb": 1000},  # Unlimited
                limits={"max_users": -1, "max_projects": -1},  # Unlimited  # Unlimited
            ),
        }
        return tiers.get(tier_id)
