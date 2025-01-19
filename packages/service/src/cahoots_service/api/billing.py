"""Billing API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from src.dependencies import get_db, get_stripe_client, get_event_system
from src.schemas.billing import (
    SubscriptionResponse,
    PaymentMethodResponse,
    InvoiceResponse,
    UsageResponse,
    BillingPortalResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    PaymentMethodCreate
)

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> SubscriptionResponse:
    """Get subscription details."""
    try:
        subscription = await stripe.get_subscription(subscription_id)
        return SubscriptionResponse(**subscription)
    except stripe.error.StripeError as e:
        raise e

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionCreate,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> SubscriptionResponse:
    """Create a new subscription."""
    try:
        subscription = await stripe.create_subscription(
            customer_id=data.customer_id,
            price_id=data.price_id,
            payment_method_id=data.payment_method_id
        )
        return SubscriptionResponse(**subscription)
    except stripe.error.StripeError as e:
        raise e

@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> SubscriptionResponse:
    """Update subscription details."""
    try:
        subscription = await stripe.update_subscription(
            subscription_id=subscription_id,
            price_id=data.price_id
        )
        return SubscriptionResponse(**subscription)
    except stripe.error.StripeError as e:
        raise e

@router.delete("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> SubscriptionResponse:
    """Cancel a subscription."""
    try:
        subscription = await stripe.cancel_subscription(subscription_id)
        return SubscriptionResponse(**subscription)
    except stripe.error.StripeError as e:
        raise e

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    customer_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> List[PaymentMethodResponse]:
    """List customer payment methods."""
    try:
        methods = await stripe.list_payment_methods(customer_id)
        return [PaymentMethodResponse(**method) for method in methods]
    except stripe.error.StripeError as e:
        raise e

@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    data: PaymentMethodCreate,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> PaymentMethodResponse:
    """Add a new payment method."""
    try:
        method = await stripe.attach_payment_method(
            payment_method_id=data.payment_method_id,
            customer_id=data.customer_id
        )
        return PaymentMethodResponse(**method)
    except stripe.error.StripeError as e:
        raise e

@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> bool:
    """Remove a payment method."""
    try:
        await stripe.detach_payment_method(payment_method_id)
        return True
    except stripe.error.StripeError as e:
        raise e

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    customer_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> List[InvoiceResponse]:
    """List customer invoices."""
    try:
        invoices = await stripe.list_invoices(customer_id)
        return [InvoiceResponse(**invoice) for invoice in invoices]
    except stripe.error.StripeError as e:
        raise e

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> InvoiceResponse:
    """Get invoice details."""
    try:
        invoice = await stripe.get_invoice(invoice_id)
        return InvoiceResponse(**invoice)
    except stripe.error.StripeError as e:
        raise e

@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(
    invoice_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> InvoiceResponse:
    """Pay an invoice."""
    try:
        invoice = await stripe.pay_invoice(invoice_id)
        return InvoiceResponse(**invoice)
    except stripe.error.StripeError as e:
        raise e

@router.get("/usage/{subscription_id}", response_model=UsageResponse)
async def get_usage(
    subscription_id: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> UsageResponse:
    """Get subscription usage details."""
    try:
        usage = await stripe.get_subscription_usage(subscription_id)
        return UsageResponse(**usage)
    except stripe.error.StripeError as e:
        raise e

@router.get("/portal", response_model=BillingPortalResponse)
async def get_billing_portal(
    customer_id: str,
    return_url: str,
    stripe=Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system=Depends(get_event_system)
) -> BillingPortalResponse:
    """Generate billing portal URL."""
    try:
        portal = await stripe.create_billing_portal(
            customer_id=customer_id,
            return_url=return_url
        )
        return BillingPortalResponse(**portal)
    except stripe.error.StripeError as e:
        raise e 
