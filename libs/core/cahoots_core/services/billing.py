"""Billing service for managing subscriptions and payments."""
import logging
from typing import Dict, List, Optional
from uuid import UUID

from cahoots_core.exceptions import ServiceError
from cahoots_core.models.db_models import Organization, Subscription, Invoice, UsageRecord
from cahoots_core.models.billing import (
    Customer,
    PaymentMethod,
    SubscriptionPlan,
    SubscriptionStatus,
    PaymentStatus,
    SubscriptionTier
)
from cahoots_core.utils.infrastructure.stripe.client import StripeClient

logger = logging.getLogger(__name__)

class BillingService:
    """Service for managing billing operations."""
    
    def __init__(self, stripe_client: StripeClient):
        """Initialize billing service."""
        self.stripe = stripe_client
        
    async def create_customer(self, user_id: UUID, email: str, name: str) -> Customer:
        """Create a new customer."""
        try:
            customer = await self.stripe.create_customer(
                user_id=str(user_id),
                email=email,
                name=name,
            )
            return Customer(
                id=customer.get("id"),
                user_id=user_id,
                email=email,
                name=name,
            )
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise ServiceError(f"Failed to create customer: {e}")
            
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer details."""
        try:
            customer = await self.stripe.get_customer(customer_id)
            if not customer:
                return None
            return Customer(
                id=customer["id"],
                user_id=UUID(customer["metadata"]["user_id"]),
                email=customer["email"],
                name=customer["name"],
            )
        except Exception as e:
            logger.error(f"Error getting customer: {e}")
            raise ServiceError(f"Failed to get customer: {e}")
            
    async def update_customer(self, customer_id: str, **kwargs) -> Customer:
        """Update customer details."""
        try:
            customer = await self.stripe.update_customer(customer_id, **kwargs)
            return Customer(
                id=customer["id"],
                user_id=UUID(customer["metadata"]["user_id"]),
                email=customer["email"],
                name=customer["name"],
            )
        except Exception as e:
            logger.error(f"Error updating customer: {e}")
            raise ServiceError(f"Failed to update customer: {e}")
            
    async def delete_customer(self, customer_id: str) -> bool:
        """Delete a customer."""
        try:
            return await self.stripe.delete_customer(customer_id)
        except Exception as e:
            logger.error(f"Error deleting customer: {e}")
            raise ServiceError(f"Failed to delete customer: {e}")
            
    async def create_payment_method(
        self, customer_id: str, payment_token: str
    ) -> PaymentMethod:
        """Create a new payment method."""
        try:
            payment = await self.stripe.create_payment_method(
                customer_id=customer_id,
                payment_token=payment_token,
            )
            return PaymentMethod(
                id=payment.get("id"),
                customer_id=customer_id,
                type=payment.get("type"),
                last4=payment.get("card", {}).get("last4"),
                exp_month=payment.get("card", {}).get("exp_month"),
                exp_year=payment.get("card", {}).get("exp_year"),
            )
        except Exception as e:
            logger.error(f"Error creating payment method: {e}")
            raise ServiceError(f"Failed to create payment method: {e}")
            
    async def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        payment_method_id: str,
    ) -> Subscription:
        """Create a new subscription."""
        try:
            sub = await self.stripe.create_subscription(
                customer_id=customer_id,
                plan_id=plan_id,
                payment_method_id=payment_method_id,
            )
            return Subscription(
                id=sub.get("id"),
                customer_id=customer_id,
                plan_id=plan_id,
                status=SubscriptionStatus(sub.get("status")),
                current_period_start=sub.get("current_period_start"),
                current_period_end=sub.get("current_period_end"),
            )
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise ServiceError(f"Failed to create subscription: {e}")
            
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription details."""
        try:
            sub = await self.stripe.get_subscription(subscription_id)
            if not sub:
                return None
            return Subscription(
                id=sub["id"],
                customer_id=sub["customer"],
                plan_id=sub["plan"]["id"],
                status=SubscriptionStatus(sub["status"]),
                current_period_start=sub["current_period_start"],
                current_period_end=sub["current_period_end"],
            )
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            raise ServiceError(f"Failed to get subscription: {e}")
            
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        try:
            return await self.stripe.cancel_subscription(subscription_id)
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            raise ServiceError(f"Failed to cancel subscription: {e}")
            
    async def list_subscriptions(self, customer_id: str) -> List[Subscription]:
        """List all subscriptions for a customer."""
        try:
            subs = await self.stripe.list_subscriptions(customer_id)
            return [
                Subscription(
                    id=sub["id"],
                    customer_id=customer_id,
                    plan_id=sub["plan"]["id"],
                    status=SubscriptionStatus(sub["status"]),
                    current_period_start=sub["current_period_start"],
                    current_period_end=sub["current_period_end"],
                )
                for sub in subs
            ]
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            raise ServiceError(f"Failed to list subscriptions: {e}")
            
    async def get_subscription_plans(self) -> List[SubscriptionPlan]:
        """Get available subscription plans."""
        try:
            plans = await self.stripe.list_plans()
            return [
                SubscriptionPlan(
                    id=plan.get("id"),
                    name=plan.get("nickname"),
                    amount=plan.get("amount"),
                    currency=plan.get("currency"),
                    interval=plan.get("interval"),
                )
                for plan in plans
            ]
        except Exception as e:
            logger.error(f"Error getting subscription plans: {e}")
            raise ServiceError(f"Failed to get subscription plans: {e}") 