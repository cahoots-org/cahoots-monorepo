"""Billing schemas."""
from typing import Dict, Optional
from pydantic import BaseModel, Field

class SubscriptionCreate(BaseModel):
    """Subscription creation schema."""
    customer_id: str = Field(..., description="Stripe customer ID")
    price_id: str = Field(..., description="Stripe price ID")
    payment_method_id: Optional[str] = Field(None, description="Optional payment method ID")

class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    price_id: str = Field(..., description="New price ID")

class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    id: str = Field(..., description="Subscription ID")
    customer_id: str = Field(..., description="Customer ID")
    price_id: str = Field(..., description="Price ID")
    status: str = Field(..., description="Subscription status")
    current_period_end: str = Field(..., description="Current period end")

    @classmethod
    def from_stripe(cls, subscription: Dict) -> "SubscriptionResponse":
        """Create response from Stripe subscription.
        
        Args:
            subscription: Stripe subscription object
            
        Returns:
            Subscription response
        """
        return cls(
            id=subscription.id,
            customer_id=subscription.customer,
            price_id=subscription.items.data[0].price.id,
            status=subscription.status,
            current_period_end=subscription.current_period_end
        )

class PaymentMethodCreate(BaseModel):
    """Payment method creation schema."""
    payment_method_id: str = Field(..., description="Payment method ID")
    customer_id: str = Field(..., description="Customer ID")

class PaymentMethodResponse(BaseModel):
    """Payment method response schema."""
    id: str = Field(..., description="Payment method ID")
    type: str = Field(..., description="Payment method type")
    card: Dict = Field(..., description="Card details")

    @classmethod
    def from_stripe(cls, payment_method: Dict) -> "PaymentMethodResponse":
        """Create response from Stripe payment method.
        
        Args:
            payment_method: Stripe payment method object
            
        Returns:
            Payment method response
        """
        return cls(
            id=payment_method.id,
            type=payment_method.type,
            card={
                "brand": payment_method.card.brand,
                "last4": payment_method.card.last4,
                "exp_month": payment_method.card.exp_month,
                "exp_year": payment_method.card.exp_year
            }
        )

class InvoiceResponse(BaseModel):
    """Invoice response schema."""
    id: str = Field(..., description="Invoice ID")
    customer_id: str = Field(..., description="Customer ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    amount_due: int = Field(..., description="Amount due in cents")
    status: str = Field(..., description="Invoice status")
    created: str = Field(..., description="Creation timestamp")

    @classmethod
    def from_stripe(cls, invoice: Dict) -> "InvoiceResponse":
        """Create response from Stripe invoice.
        
        Args:
            invoice: Stripe invoice object
            
        Returns:
            Invoice response
        """
        return cls(
            id=invoice.id,
            customer_id=invoice.customer,
            subscription_id=invoice.subscription,
            amount_due=invoice.amount_due,
            status=invoice.status,
            created=invoice.created
        )

class BillingPortalResponse(BaseModel):
    """Billing portal response schema."""
    url: str = Field(..., description="Billing portal URL")

class UsageResponse(BaseModel):
    """Usage response schema."""
    subscription_id: str = Field(..., description="Subscription ID")
    current_usage: int = Field(..., description="Current usage")
    limit: int = Field(..., description="Usage limit")
    period_start: str = Field(..., description="Period start timestamp")
    period_end: str = Field(..., description="Period end timestamp")

    @classmethod
    def from_stripe(cls, usage: Dict) -> "UsageResponse":
        """Create response from Stripe usage.
        
        Args:
            usage: Stripe usage object
            
        Returns:
            Usage response
        """
        return cls(
            subscription_id=usage.subscription,
            current_usage=usage.total_usage,
            limit=usage.quota.limit,
            period_start=usage.period.start,
            period_end=usage.period.end
        ) 