"""Billing API schemas."""
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

class SubscriptionCreate(BaseModel):
    """Subscription creation request."""
    customer_id: str = Field(..., description="Stripe customer ID")
    price_id: str = Field(..., description="Stripe price ID")
    payment_method_id: str = Field(..., description="Stripe payment method ID")

class SubscriptionUpdate(BaseModel):
    """Subscription update request."""
    price_id: str = Field(..., description="New Stripe price ID")

class SubscriptionResponse(BaseModel):
    """Subscription response."""
    id: str = Field(..., description="Subscription ID")
    customer_id: str = Field(..., description="Customer ID")
    price_id: str = Field(..., description="Price ID")
    status: str = Field(..., description="Subscription status")
    current_period_end: int = Field(..., description="Current period end timestamp")
    cancel_at_period_end: bool = Field(..., description="Whether subscription will cancel at period end")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Subscription metadata")

class PaymentMethodCreate(BaseModel):
    """Payment method creation request."""
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    customer_id: str = Field(..., description="Stripe customer ID")

class PaymentMethodResponse(BaseModel):
    """Payment method response."""
    id: str = Field(..., description="Payment method ID")
    type: str = Field(..., description="Payment method type")
    card: Dict[str, Any] = Field(..., description="Card details")
    billing_details: Dict[str, Any] = Field(..., description="Billing details")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Payment method metadata")

class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: str = Field(..., description="Invoice ID")
    customer_id: str = Field(..., description="Customer ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    status: str = Field(..., description="Invoice status")
    amount_due: int = Field(..., description="Amount due in cents")
    amount_paid: int = Field(..., description="Amount paid in cents")
    created: int = Field(..., description="Creation timestamp")
    due_date: Optional[int] = Field(None, description="Due date timestamp")
    hosted_invoice_url: Optional[str] = Field(None, description="URL to hosted invoice page")
    pdf_url: Optional[str] = Field(None, description="URL to download PDF invoice")

class UsageResponse(BaseModel):
    """Usage response."""
    subscription_id: str = Field(..., description="Subscription ID")
    period_start: int = Field(..., description="Period start timestamp")
    period_end: int = Field(..., description="Period end timestamp")
    total_usage: int = Field(..., description="Total usage in units")
    items: List[Dict[str, Any]] = Field(..., description="Usage items")

class BillingPortalResponse(BaseModel):
    """Billing portal response."""
    url: str = Field(..., description="URL to Stripe billing portal")
    return_url: str = Field(..., description="URL to return to after portal session") 