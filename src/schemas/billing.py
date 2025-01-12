"""Billing schemas for request/response validation."""
from typing import Dict, Optional
from pydantic import BaseModel, Field

class CardDetails(BaseModel):
    """Card payment method details."""
    brand: str
    last4: str
    exp_month: int
    exp_year: int

class PaymentMethodResponse(BaseModel):
    """Payment method details."""
    id: str
    type: str
    card: Optional[CardDetails] = None

class PaymentMethodCreate(BaseModel):
    """Payment method creation parameters."""
    payment_method_id: str
    customer_id: str

class SubscriptionResponse(BaseModel):
    """Subscription details."""
    id: str
    customer_id: str
    price_id: str
    status: str
    current_period_end: str

class SubscriptionCreate(BaseModel):
    """Subscription creation parameters."""
    customer_id: str
    price_id: str
    payment_method_id: str

class SubscriptionUpdate(BaseModel):
    """Subscription update parameters."""
    price_id: str

class InvoiceResponse(BaseModel):
    """Invoice details."""
    id: str
    customer_id: str
    subscription_id: str
    amount_due: int
    status: str
    created: str

class UsageResponse(BaseModel):
    """Subscription usage details."""
    subscription_id: str
    current_usage: int
    limit: int
    period_start: str
    period_end: str

class BillingPortalResponse(BaseModel):
    """Billing portal session details."""
    url: str 