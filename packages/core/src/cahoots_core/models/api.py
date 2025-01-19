"""API request/response models."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

class PaymentMethodRequest(BaseModel):
    """Payment method request model."""
    token: str = Field(..., description="Payment method token")
    set_default: bool = Field(False, description="Whether to set as default payment method")
    
    @validator("token")
    def validate_token(cls, v):
        """Validate payment method token."""
        if not v.startswith("tok_"):
            raise ValueError("Invalid payment method token format")
        return v

class SubscriptionRequest(BaseModel):
    """Subscription request model."""
    tier_id: str = Field(..., description="Subscription tier ID")
    payment_method_id: str = Field(..., description="Payment method ID")
    is_yearly: bool = Field(False, description="Whether subscription is yearly")
    
    @validator("tier_id")
    def validate_tier_id(cls, v):
        """Validate tier ID."""
        valid_tiers = ["free", "pro", "enterprise"]
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier ID. Must be one of: {', '.join(valid_tiers)}")
        return v
    
    @validator("payment_method_id")
    def validate_payment_method_id(cls, v):
        """Validate payment method ID."""
        if not v.startswith("pm_"):
            raise ValueError("Invalid payment method ID format")
        return v

class SubscriptionUpdateRequest(BaseModel):
    """Subscription update request model."""
    tier_id: str = Field(..., description="New subscription tier ID")
    is_yearly: bool = Field(False, description="Whether subscription is yearly")
    
    @validator("tier_id")
    def validate_tier_id(cls, v):
        """Validate tier ID."""
        valid_tiers = ["free", "pro", "enterprise"]
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier ID. Must be one of: {', '.join(valid_tiers)}")
        return v

class UsageQueryParams(BaseModel):
    """Usage query parameters."""
    metric: str = Field(..., description="Usage metric to query")
    start_time: datetime = Field(..., description="Start time for usage query")
    end_time: datetime = Field(..., description="End time for usage query")
    
    @validator("metric")
    def validate_metric(cls, v):
        """Validate usage metric."""
        valid_metrics = ["api_calls", "storage", "compute_time"]
        if v not in valid_metrics:
            raise ValueError(f"Invalid metric. Must be one of: {', '.join(valid_metrics)}")
        return v
    
    @validator("end_time")
    def validate_time_range(cls, v, values):
        """Validate time range."""
        if "start_time" in values and v < values["start_time"]:
            raise ValueError("End time must be after start time")
        return v

class InvoiceQueryParams(BaseModel):
    """Invoice query parameters."""
    status: Optional[str] = Field(None, description="Filter by invoice status")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of invoices to return")
    
    @validator("status")
    def validate_status(cls, v):
        """Validate invoice status."""
        if v:
            valid_statuses = ["draft", "open", "paid", "void", "uncollectible"]
            if v not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return v
    
    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and "start_date" in values and values["start_date"] and v < values["start_date"]:
            raise ValueError("End date must be after start date")
        return v 