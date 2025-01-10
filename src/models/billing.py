"""Billing models."""
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

class SubscriptionTier(BaseModel):
    """Subscription tier configuration."""
    id: str = Field(..., description="Unique tier identifier")
    name: str = Field(..., description="Tier name (free, pro, enterprise)")
    price_monthly: Decimal = Field(..., description="Monthly price in USD")
    price_yearly: Decimal = Field(..., description="Yearly price in USD")
    features: Dict[str, Any] = Field(..., description="Features included in this tier")
    limits: Dict[str, Any] = Field(..., description="Resource limits for this tier")

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
    id: str
    organization_id: str
    metric: str
    quantity: int
    timestamp: datetime 