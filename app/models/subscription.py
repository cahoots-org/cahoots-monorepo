"""Subscription models for tier-based access control."""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    HOBBYIST = "hobbyist"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class Subscription(BaseModel):
    """User subscription details."""
    tier: SubscriptionTier = SubscriptionTier.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

    class Config:
        use_enum_values = True


class CheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    price_id: str = Field(..., description="Stripe price ID for the plan")
    success_url: Optional[str] = Field(None, description="URL to redirect after success")
    cancel_url: Optional[str] = Field(None, description="URL to redirect after cancel")


class CheckoutResponse(BaseModel):
    """Response with Stripe checkout session URL."""
    checkout_url: str
    session_id: str


class EmbeddedCheckoutRequest(BaseModel):
    """Request to create an embedded Stripe checkout session."""
    price_id: str = Field(..., description="Stripe price ID for the plan")
    return_url: Optional[str] = Field(None, description="URL to redirect after checkout")


class EmbeddedCheckoutResponse(BaseModel):
    """Response with client secret for embedded checkout."""
    client_secret: str
    session_id: str


class CheckoutStatusResponse(BaseModel):
    """Response with checkout session status."""
    status: str
    customer_email: Optional[str] = None
    subscription_id: Optional[str] = None


class PortalResponse(BaseModel):
    """Response with Stripe billing portal URL."""
    portal_url: str


class PlanInfo(BaseModel):
    """Information about a subscription plan."""
    id: str
    name: str
    description: str
    price_monthly: Optional[int] = None  # Price in cents
    price_yearly: Optional[int] = None   # Price in cents
    features: list[str]
    is_popular: bool = False
    cta_text: str = "Get Started"
    stripe_price_id: Optional[str] = None


class PlansResponse(BaseModel):
    """Response containing all available plans."""
    plans: list[PlanInfo]


# Feature flags by tier
TIER_FEATURES = {
    SubscriptionTier.FREE: {
        "task_decomposition": True,
        "event_modeling": True,
        "code_generation": False,
        "github_integration": False,
        "export": False,
        "api_access": False,
        "priority_support": False,
        "custom_integrations": False,
        "sso": False,
    },
    SubscriptionTier.HOBBYIST: {
        "task_decomposition": True,
        "event_modeling": True,
        "code_generation": False,
        "github_integration": False,
        "export": True,
        "api_access": False,
        "priority_support": False,
        "custom_integrations": False,
        "sso": False,
    },
    SubscriptionTier.PRO: {
        "task_decomposition": True,
        "event_modeling": True,
        "code_generation": True,
        "github_integration": True,
        "export": True,
        "api_access": True,
        "priority_support": False,
        "custom_integrations": False,
        "sso": False,
    },
    SubscriptionTier.ENTERPRISE: {
        "task_decomposition": True,
        "event_modeling": True,
        "code_generation": True,
        "github_integration": True,
        "export": True,
        "api_access": True,
        "priority_support": True,
        "custom_integrations": True,
        "sso": True,
    },
}


def get_tier_features(tier: SubscriptionTier) -> dict:
    """Get feature flags for a subscription tier."""
    return TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])


def has_feature(tier: SubscriptionTier, feature: str) -> bool:
    """Check if a tier has access to a specific feature."""
    features = get_tier_features(tier)
    return features.get(feature, False)


# Plan definitions for pricing page
PLANS = [
    PlanInfo(
        id="free",
        name="Free",
        description="Perfect for trying out Cahoots",
        price_monthly=0,
        features=[
            "Task decomposition",
            "Event modeling",
            "Unlimited projects",
            "Community support",
        ],
        cta_text="Get Started",
    ),
    PlanInfo(
        id="hobbyist",
        name="Hobbyist",
        description="For side projects and personal use",
        price_monthly=1000,  # $10.00
        price_yearly=10000,  # $100.00 (2 months free)
        features=[
            "Everything in Free",
            "Export to JSON/Markdown",
            "Email support",
        ],
        cta_text="Upgrade to Hobbyist",
    ),
    PlanInfo(
        id="pro",
        name="Pro",
        description="For professional developers and teams",
        price_monthly=5000,  # $50.00
        price_yearly=50000,  # $500.00 (2 months free)
        features=[
            "Everything in Hobbyist",
            "Code generation",
            "GitHub integration",
            "API access",
            "Priority email support",
        ],
        is_popular=True,
        cta_text="Upgrade to Pro",
    ),
    PlanInfo(
        id="enterprise",
        name="Enterprise",
        description="For large teams with custom needs",
        price_monthly=None,  # Contact sales
        features=[
            "Everything in Pro",
            "SSO/SAML authentication",
            "Custom integrations",
            "Priority support",
            "Dedicated account manager",
            "Custom contracts",
            "SLA guarantees",
        ],
        cta_text="Contact Sales",
    ),
]
