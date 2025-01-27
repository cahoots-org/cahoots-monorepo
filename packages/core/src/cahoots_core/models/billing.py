"""Billing models."""
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class Customer(BaseModel):
    """Customer model."""
    id: str = Field(..., description="Stripe customer ID")
    user_id: UUID = Field(..., description="Associated user ID")
    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")

class SubscriptionTier(BaseModel):
    """Subscription tier configuration."""
    id: str = Field(..., description="Unique tier identifier")
    name: str = Field(..., description="Tier name (free, pro, enterprise)")
    price_monthly: Decimal = Field(..., description="Monthly price in USD")
    price_yearly: Decimal = Field(..., description="Yearly price in USD")
    features: Dict[str, Any] = Field(..., description="Features included in this tier")
    limits: Dict[str, Any] = Field(..., description="Resource limits for this tier")

class SubscriptionPlan(BaseModel):
    """Subscription plan model."""
    id: str = Field(..., description="Unique plan identifier")
    tier_id: str = Field(..., description="Associated tier ID")
    interval: str = Field(..., description="Billing interval (monthly/yearly)")
    price: Decimal = Field(..., description="Price in USD")
    active: bool = Field(True, description="Whether this plan is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional plan metadata")

class Subscription(BaseModel):
    """Subscription model."""
    id: str
    customer_id: str
    plan_id: str
    status: str
    current_period_end: str

class PaymentMethod(BaseModel):
    """Payment method model."""
    id: str
    type: str
    card: Dict[str, Any]

class Invoice(BaseModel):
    """Invoice model."""
    id: str
    customer_id: str
    subscription_id: str
    amount_due: int
    status: str
    created: str

class Usage(BaseModel):
    """Usage model."""
    subscription_id: str
    current_usage: int
    limit: int
    period_start: str
    period_end: str

class BillingPortal(BaseModel):
    """Billing portal model."""
    url: str

class UsageRecord(BaseModel):
    """Usage record model."""
    id: str = Field(..., description="Unique usage record ID")
    organization_id: str = Field(..., description="Organization ID")
    metric: str = Field(..., description="Usage metric name")
    quantity: int = Field(..., description="Usage quantity")
    timestamp: datetime = Field(..., description="When the usage occurred")

class BillingInfo(BaseModel):
    """Billing information model."""
    customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    subscription_id: Optional[str] = Field(None, description="Active subscription ID")
    payment_method_id: Optional[str] = Field(None, description="Default payment method ID")
    email: Optional[str] = Field(None, description="Billing email")
    name: Optional[str] = Field(None, description="Billing name")
    address: Optional[Dict[str, Any]] = Field(None, description="Billing address")

class SubscriptionStatus:
    """Subscription status constants."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"

class PaymentStatus:
    """Payment status constants."""
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled" 