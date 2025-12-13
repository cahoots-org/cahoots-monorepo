"""Stripe configuration and utilities."""

import os
from typing import Optional

import stripe


# Initialize Stripe with API key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs from Stripe Dashboard
STRIPE_PRICE_HOBBYIST_MONTHLY = os.getenv("STRIPE_PRICE_HOBBYIST_MONTHLY", "")
STRIPE_PRICE_HOBBYIST_YEARLY = os.getenv("STRIPE_PRICE_HOBBYIST_YEARLY", "")
STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
STRIPE_PRICE_PRO_YEARLY = os.getenv("STRIPE_PRICE_PRO_YEARLY", "")

# Redirect URLs
STRIPE_SUCCESS_URL = os.getenv(
    "STRIPE_SUCCESS_URL",
    "http://localhost:3000/settings/billing?success=true"
)
STRIPE_CANCEL_URL = os.getenv(
    "STRIPE_CANCEL_URL",
    "http://localhost:3000/pricing?canceled=true"
)

# Initialize stripe client
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_PRO_MONTHLY)


def get_stripe_client() -> Optional[stripe]:
    """Get the configured Stripe client."""
    if not is_stripe_configured():
        return None
    return stripe


def create_customer(email: str, name: Optional[str] = None, user_id: Optional[str] = None) -> stripe.Customer:
    """Create a new Stripe customer."""
    metadata = {}
    if user_id:
        metadata["user_id"] = user_id

    return stripe.Customer.create(
        email=email,
        name=name,
        metadata=metadata,
    )


def get_or_create_customer(
    email: str,
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    existing_customer_id: Optional[str] = None
) -> stripe.Customer:
    """Get existing customer or create a new one."""
    if existing_customer_id:
        try:
            return stripe.Customer.retrieve(existing_customer_id)
        except stripe.error.InvalidRequestError:
            pass  # Customer doesn't exist, create new one

    # Search for existing customer by email
    customers = stripe.Customer.list(email=email, limit=1)
    if customers.data:
        return customers.data[0]

    return create_customer(email, name, user_id)


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> stripe.checkout.Session:
    """Create a Stripe checkout session for subscription."""
    return stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url=success_url or STRIPE_SUCCESS_URL,
        cancel_url=cancel_url or STRIPE_CANCEL_URL,
        allow_promotion_codes=True,
    )


def create_embedded_checkout_session(
    customer_id: str,
    price_id: str,
    return_url: Optional[str] = None,
) -> stripe.checkout.Session:
    """Create an embedded Stripe checkout session for subscription.

    Uses ui_mode='embedded' for inline payment form.
    The return_url should include {CHECKOUT_SESSION_ID} placeholder.
    """
    # Default return URL with session ID placeholder
    default_return_url = "http://localhost:3000/checkout/return?session_id={CHECKOUT_SESSION_ID}"

    return stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        ui_mode="embedded",
        return_url=return_url or default_return_url,
        allow_promotion_codes=True,
    )


def get_checkout_session(session_id: str) -> stripe.checkout.Session:
    """Retrieve a checkout session by ID."""
    return stripe.checkout.Session.retrieve(session_id)


def create_portal_session(customer_id: str, return_url: Optional[str] = None) -> stripe.billing_portal.Session:
    """Create a Stripe billing portal session."""
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url or STRIPE_SUCCESS_URL.replace("?success=true", ""),
    )


def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> stripe.Subscription:
    """Cancel a subscription."""
    if at_period_end:
        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
    else:
        return stripe.Subscription.delete(subscription_id)


def get_subscription(subscription_id: str) -> stripe.Subscription:
    """Get subscription details."""
    return stripe.Subscription.retrieve(subscription_id)


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify and parse a Stripe webhook event."""
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        STRIPE_WEBHOOK_SECRET,
    )
