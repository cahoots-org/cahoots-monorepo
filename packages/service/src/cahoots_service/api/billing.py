"""Billing API endpoints."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.exceptions import ServiceError
from cahoots_core.utils.infrastructure.stripe.client import StripeClient, StripeError
from cahoots_events.bus.system import EventSystem
from cahoots_service.api.dependencies import (
    get_db,
    get_event_bus,
    get_organization_id
)
from cahoots_service.schemas.billing import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    InvoiceResponse,
    UsageResponse,
    BillingPortalResponse
)

router = APIRouter(prefix="/api/billing", tags=["billing"])

async def get_stripe_client() -> StripeClient:
    """Get Stripe client instance."""
    return StripeClient()

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> SubscriptionResponse:
    """Get subscription details.
    
    Args:
        subscription_id: Subscription identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Subscription details
        
    Raises:
        HTTPException: If subscription not found or other error occurs
    """
    try:
        subscription = await stripe.get_subscription(subscription_id)
        return SubscriptionResponse(**subscription)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription: {str(e)}"
        )

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionCreate,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> SubscriptionResponse:
    """Create a new subscription.
    
    Args:
        data: Subscription creation data
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Created subscription details
        
    Raises:
        HTTPException: If subscription creation fails
    """
    try:
        subscription = await stripe.create_subscription(
            customer_id=data.customer_id,
            price_id=data.price_id,
            payment_method_id=data.payment_method_id
        )
        return SubscriptionResponse(**subscription)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> SubscriptionResponse:
    """Update subscription details.
    
    Args:
        subscription_id: Subscription identifier
        data: Subscription update data
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Updated subscription details
        
    Raises:
        HTTPException: If subscription update fails
    """
    try:
        subscription = await stripe.update_subscription(
            subscription_id=subscription_id,
            price_id=data.price_id
        )
        return SubscriptionResponse(**subscription)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )

@router.delete("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> SubscriptionResponse:
    """Cancel a subscription.
    
    Args:
        subscription_id: Subscription identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Cancelled subscription details
        
    Raises:
        HTTPException: If subscription cancellation fails
    """
    try:
        subscription = await stripe.cancel_subscription(subscription_id)
        return SubscriptionResponse(**subscription)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    customer_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> List[PaymentMethodResponse]:
    """List customer payment methods.
    
    Args:
        customer_id: Customer identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        List of payment methods
        
    Raises:
        HTTPException: If listing payment methods fails
    """
    try:
        methods = await stripe.list_payment_methods(customer_id)
        return [PaymentMethodResponse(**method) for method in methods]
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list payment methods: {str(e)}"
        )

@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    data: PaymentMethodCreate,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> PaymentMethodResponse:
    """Add a new payment method.
    
    Args:
        data: Payment method creation data
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Added payment method details
        
    Raises:
        HTTPException: If adding payment method fails
    """
    try:
        method = await stripe.attach_payment_method(
            payment_method_id=data.payment_method_id,
            customer_id=data.customer_id
        )
        return PaymentMethodResponse(**method)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment method: {str(e)}"
        )

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    customer_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> List[InvoiceResponse]:
    """List customer invoices.
    
    Args:
        customer_id: Customer identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        List of invoices
        
    Raises:
        HTTPException: If listing invoices fails
    """
    try:
        invoices = await stripe.list_invoices(customer_id)
        return [InvoiceResponse(**invoice) for invoice in invoices]
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list invoices: {str(e)}"
        )

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> InvoiceResponse:
    """Get invoice details.
    
    Args:
        invoice_id: Invoice identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Invoice details
        
    Raises:
        HTTPException: If invoice not found or other error occurs
    """
    try:
        invoice = await stripe.get_invoice(invoice_id)
        return InvoiceResponse(**invoice)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoice: {str(e)}"
        )

@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(
    invoice_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> InvoiceResponse:
    """Pay an invoice.
    
    Args:
        invoice_id: Invoice identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Updated invoice details
        
    Raises:
        HTTPException: If payment fails
    """
    try:
        invoice = await stripe.pay_invoice(invoice_id)
        return InvoiceResponse(**invoice)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pay invoice: {str(e)}"
        )

@router.get("/usage/{subscription_id}", response_model=UsageResponse)
async def get_usage(
    subscription_id: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> UsageResponse:
    """Get subscription usage details.
    
    Args:
        subscription_id: Subscription identifier
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Usage details
        
    Raises:
        HTTPException: If usage retrieval fails
    """
    try:
        usage = await stripe.get_subscription_usage(subscription_id)
        return UsageResponse(**usage)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage: {str(e)}"
        )

@router.get("/portal", response_model=BillingPortalResponse)
async def get_billing_portal(
    customer_id: str,
    return_url: str,
    organization_id: UUID = Depends(get_organization_id),
    stripe: StripeClient = Depends(get_stripe_client),
    db: AsyncSession = Depends(get_db),
    event_system: EventSystem = Depends(get_event_bus)
) -> BillingPortalResponse:
    """Generate billing portal URL.
    
    Args:
        customer_id: Customer identifier
        return_url: URL to return to after portal session
        organization_id: Current organization ID
        stripe: Stripe client instance
        db: Database session
        event_system: Event system instance
        
    Returns:
        Portal URL and return URL
        
    Raises:
        HTTPException: If portal creation fails
    """
    try:
        portal = await stripe.create_billing_portal(
            customer_id=customer_id,
            return_url=return_url
        )
        return BillingPortalResponse(**portal)
    except StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create billing portal: {str(e)}"
        ) 
