"""Subscription management API routes."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.api.dependencies import get_redis_client
from app.api.routes.auth import get_current_user
from app.models.subscription import (
    CheckoutRequest,
    CheckoutResponse,
    CheckoutStatusResponse,
    EmbeddedCheckoutRequest,
    EmbeddedCheckoutResponse,
    PlansResponse,
    PortalResponse,
    PLANS,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)
from app.config.stripe import (
    create_checkout_session,
    create_embedded_checkout_session,
    create_portal_session,
    get_checkout_session,
    get_or_create_customer,
    is_stripe_configured,
    verify_webhook_signature,
    STRIPE_PRICE_HOBBYIST_MONTHLY,
    STRIPE_PRICE_HOBBYIST_YEARLY,
    STRIPE_PRICE_PRO_MONTHLY,
    STRIPE_PRICE_PRO_YEARLY,
    STRIPE_PUBLISHABLE_KEY,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=PlansResponse)
async def get_plans():
    """Get all available subscription plans."""
    # Add Stripe price IDs to plans
    plans = []
    for plan in PLANS:
        plan_copy = plan.model_copy()
        if plan.id == "hobbyist" and STRIPE_PRICE_HOBBYIST_MONTHLY:
            plan_copy.stripe_price_id = STRIPE_PRICE_HOBBYIST_MONTHLY
        elif plan.id == "pro" and STRIPE_PRICE_PRO_MONTHLY:
            plan_copy.stripe_price_id = STRIPE_PRICE_PRO_MONTHLY
        plans.append(plan_copy)

    return PlansResponse(plans=plans)


@router.get("/current")
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
):
    """Get the current user's subscription details."""
    user_id = current_user.get("id") or current_user.get("sub")

    # Get subscription from user data
    user_data = await redis_client.get(f"user:{user_id}")
    if user_data:
        user = json.loads(user_data)
        subscription_data = user.get("subscription", {})
    else:
        subscription_data = {}

    # Return subscription with defaults
    return Subscription(
        tier=SubscriptionTier(subscription_data.get("tier", "free")),
        status=SubscriptionStatus(subscription_data.get("status", "active")),
        stripe_customer_id=subscription_data.get("stripe_customer_id"),
        stripe_subscription_id=subscription_data.get("stripe_subscription_id"),
        current_period_end=subscription_data.get("current_period_end"),
        cancel_at_period_end=subscription_data.get("cancel_at_period_end", False),
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
):
    """Create a Stripe checkout session for subscription."""
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )

    user_id = current_user.get("id") or current_user.get("sub")
    email = current_user.get("email")
    name = current_user.get("name")

    # Get existing customer ID from user data
    user_data = await redis_client.get(f"user:{user_id}")
    existing_customer_id = None
    if user_data:
        user = json.loads(user_data)
        existing_customer_id = user.get("subscription", {}).get("stripe_customer_id")

    try:
        # Get or create Stripe customer
        customer = get_or_create_customer(
            email=email,
            name=name,
            user_id=user_id,
            existing_customer_id=existing_customer_id,
        )

        # Update user with Stripe customer ID if new
        if not existing_customer_id and user_data:
            user = json.loads(user_data)
            if "subscription" not in user:
                user["subscription"] = {}
            user["subscription"]["stripe_customer_id"] = customer.id
            await redis_client.set(f"user:{user_id}", json.dumps(user))

        # Create checkout session
        session = create_checkout_session(
            customer_id=customer.id,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )

    except Exception as e:
        print(f"[Subscriptions] Checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )


@router.get("/config")
async def get_stripe_config():
    """Get Stripe publishable key for frontend."""
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )
    return {"publishable_key": STRIPE_PUBLISHABLE_KEY}


@router.post("/embedded-checkout", response_model=EmbeddedCheckoutResponse)
async def create_embedded_checkout(
    request: EmbeddedCheckoutRequest,
    current_user: dict = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
):
    """Create an embedded Stripe checkout session for inline payment."""
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )

    user_id = current_user.get("id") or current_user.get("sub")
    email = current_user.get("email")
    name = current_user.get("name")

    # Get existing customer ID from user data
    user_data = await redis_client.get(f"user:{user_id}")
    existing_customer_id = None
    if user_data:
        user = json.loads(user_data)
        existing_customer_id = user.get("subscription", {}).get("stripe_customer_id")

    try:
        # Get or create Stripe customer
        customer = get_or_create_customer(
            email=email,
            name=name,
            user_id=user_id,
            existing_customer_id=existing_customer_id,
        )

        # Update user with Stripe customer ID if new
        if not existing_customer_id and user_data:
            user = json.loads(user_data)
            if "subscription" not in user:
                user["subscription"] = {}
            user["subscription"]["stripe_customer_id"] = customer.id
            await redis_client.set(f"user:{user_id}", json.dumps(user))

        # Create embedded checkout session
        session = create_embedded_checkout_session(
            customer_id=customer.id,
            price_id=request.price_id,
            return_url=request.return_url,
        )

        return EmbeddedCheckoutResponse(
            client_secret=session.client_secret,
            session_id=session.id,
        )

    except Exception as e:
        print(f"[Subscriptions] Embedded checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )


@router.get("/checkout-status/{session_id}", response_model=CheckoutStatusResponse)
async def get_checkout_status(session_id: str):
    """Get the status of a checkout session."""
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )

    try:
        session = get_checkout_session(session_id)
        return CheckoutStatusResponse(
            status=session.status,
            customer_email=session.customer_details.email if session.customer_details else None,
            subscription_id=session.subscription,
        )
    except Exception as e:
        print(f"[Subscriptions] Checkout status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found",
        )


@router.post("/portal", response_model=PortalResponse)
async def create_billing_portal(
    current_user: dict = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
    return_url: Optional[str] = None,
):
    """Create a Stripe billing portal session."""
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )

    user_id = current_user.get("id") or current_user.get("sub")

    # Get customer ID from user data
    user_data = await redis_client.get(f"user:{user_id}")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = json.loads(user_data)
    customer_id = user.get("subscription", {}).get("stripe_customer_id")

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    try:
        session = create_portal_session(customer_id, return_url)
        return PortalResponse(portal_url=session.url)
    except Exception as e:
        print(f"[Subscriptions] Portal error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create billing portal session: {str(e)}",
        )


@router.post("/webhook")
async def handle_stripe_webhook(
    request: Request,
    redis_client: Redis = Depends(get_redis_client),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )

    try:
        event = verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        print(f"[Subscriptions] Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        print(f"[Subscriptions] Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    print(f"[Subscriptions] Received webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(data, redis_client)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(data, redis_client)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(data, redis_client)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(data, redis_client)
        elif event_type == "invoice.paid":
            await handle_invoice_paid(data, redis_client)
    except Exception as e:
        print(f"[Subscriptions] Webhook handler error: {e}")
        # Don't raise - return 200 so Stripe doesn't retry

    return {"status": "ok"}


def determine_tier_from_price(price_id: str) -> SubscriptionTier:
    """Determine subscription tier from Stripe price ID."""
    if price_id in (STRIPE_PRICE_HOBBYIST_MONTHLY, STRIPE_PRICE_HOBBYIST_YEARLY):
        return SubscriptionTier.HOBBYIST
    elif price_id in (STRIPE_PRICE_PRO_MONTHLY, STRIPE_PRICE_PRO_YEARLY):
        return SubscriptionTier.PRO
    # Default to Pro for unknown price IDs (enterprise or custom)
    return SubscriptionTier.PRO


async def handle_checkout_completed(session: dict, redis_client: Redis):
    """Handle successful checkout completion."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not customer_id or not subscription_id:
        print("[Subscriptions] Missing customer or subscription in checkout session")
        return

    # Find user by Stripe customer ID
    user_id = await find_user_by_customer_id(customer_id, redis_client)
    if not user_id:
        print(f"[Subscriptions] No user found for customer {customer_id}")
        return

    # Get subscription details from Stripe
    import stripe
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Determine tier from the subscription's price
    price_id = ""
    if subscription.items and subscription.items.data:
        price_id = subscription.items.data[0].price.id
    tier = determine_tier_from_price(price_id)

    # Update user subscription
    await update_user_subscription(
        user_id=user_id,
        redis_client=redis_client,
        tier=tier,
        status=SubscriptionStatus.ACTIVE,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        current_period_end=datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        ),
    )

    print(f"[Subscriptions] User {user_id} upgraded to {tier.value}")


async def handle_subscription_updated(subscription: dict, redis_client: Redis):
    """Handle subscription updates (plan changes, renewals)."""
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    status_str = subscription.get("status")

    user_id = await find_user_by_customer_id(customer_id, redis_client)
    if not user_id:
        return

    # Map Stripe status to our status
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "trialing": SubscriptionStatus.TRIALING,
        "incomplete": SubscriptionStatus.INCOMPLETE,
    }
    status = status_map.get(status_str, SubscriptionStatus.ACTIVE)

    # Determine tier from price (for plan changes)
    items = subscription.get("items", {}).get("data", [])
    price_id = items[0].get("price", {}).get("id", "") if items else ""
    tier = determine_tier_from_price(price_id) if price_id else None

    await update_user_subscription(
        user_id=user_id,
        redis_client=redis_client,
        tier=tier,
        status=status,
        stripe_subscription_id=subscription_id,
        current_period_end=datetime.fromtimestamp(
            subscription.get("current_period_end", 0), tz=timezone.utc
        ),
        cancel_at_period_end=subscription.get("cancel_at_period_end", False),
    )

    print(f"[Subscriptions] Updated subscription for user {user_id}: {status}, tier: {tier.value if tier else 'unchanged'}")


async def handle_subscription_deleted(subscription: dict, redis_client: Redis):
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")

    user_id = await find_user_by_customer_id(customer_id, redis_client)
    if not user_id:
        return

    await update_user_subscription(
        user_id=user_id,
        redis_client=redis_client,
        tier=SubscriptionTier.FREE,
        status=SubscriptionStatus.CANCELED,
        stripe_subscription_id=None,
        current_period_end=None,
    )

    print(f"[Subscriptions] User {user_id} downgraded to Free")


async def handle_payment_failed(invoice: dict, redis_client: Redis):
    """Handle failed payment."""
    customer_id = invoice.get("customer")

    user_id = await find_user_by_customer_id(customer_id, redis_client)
    if not user_id:
        return

    await update_user_subscription(
        user_id=user_id,
        redis_client=redis_client,
        status=SubscriptionStatus.PAST_DUE,
    )

    print(f"[Subscriptions] Payment failed for user {user_id}")


async def handle_invoice_paid(invoice: dict, redis_client: Redis):
    """Handle successful invoice payment."""
    customer_id = invoice.get("customer")

    user_id = await find_user_by_customer_id(customer_id, redis_client)
    if not user_id:
        return

    await update_user_subscription(
        user_id=user_id,
        redis_client=redis_client,
        status=SubscriptionStatus.ACTIVE,
    )

    print(f"[Subscriptions] Invoice paid for user {user_id}")


async def find_user_by_customer_id(customer_id: str, redis_client: Redis) -> Optional[str]:
    """Find a user ID by their Stripe customer ID."""
    # This is inefficient but works for now
    # In production, you'd want a customer_id -> user_id index
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="user:*", count=100)
        for key in keys:
            if key.startswith(b"user:email:"):
                continue
            user_data = await redis_client.get(key)
            if user_data:
                user = json.loads(user_data)
                if user.get("subscription", {}).get("stripe_customer_id") == customer_id:
                    return user.get("id")
        if cursor == 0:
            break
    return None


async def update_user_subscription(
    user_id: str,
    redis_client: Redis,
    tier: Optional[SubscriptionTier] = None,
    status: Optional[SubscriptionStatus] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_period_end: Optional[datetime] = None,
    cancel_at_period_end: Optional[bool] = None,
):
    """Update a user's subscription data."""
    user_data = await redis_client.get(f"user:{user_id}")
    if not user_data:
        return

    user = json.loads(user_data)

    if "subscription" not in user:
        user["subscription"] = {}

    if tier is not None:
        user["subscription"]["tier"] = tier.value
    if status is not None:
        user["subscription"]["status"] = status.value
    if stripe_customer_id is not None:
        user["subscription"]["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id is not None:
        user["subscription"]["stripe_subscription_id"] = stripe_subscription_id
    if current_period_end is not None:
        user["subscription"]["current_period_end"] = current_period_end.isoformat()
    if cancel_at_period_end is not None:
        user["subscription"]["cancel_at_period_end"] = cancel_at_period_end

    await redis_client.set(f"user:{user_id}", json.dumps(user))
