"""Billing API endpoints for subscription and payment management.

This module provides REST endpoints for managing billing operations including:
- Subscription management (create, read, update, delete)
- Payment method management
- Invoice operations
- Usage tracking
- Billing portal access
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
import stripe

from src.api.dependencies import (
    DBSession,
    EventSystemDep,
    StripeClientDep,
    get_session,
    get_verified_event_system as get_event_system,
    get_stripe_client
)
from src.schemas.billing import (
    PaymentMethodCreate,
    PaymentMethodResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    InvoiceResponse,
    BillingPortalResponse,
    UsageResponse
)

router = APIRouter(prefix="/billing", tags=["billing"])

@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionCreate,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> SubscriptionResponse:
    """Create a new subscription for a customer.
    
    Args:
        data: Subscription creation parameters including customer ID and price ID
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        SubscriptionResponse: Details of the created subscription
        
    Raises:
        HTTPException(400): If subscription creation fails due to invalid parameters
        HTTPException(402): If payment processing fails
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        subscription = stripe.create_subscription(
            customer_id=data.customer_id,
            price_id=data.price_id,
            payment_method_id=data.payment_method_id
        )
        await event_system.emit("subscription.created", {
            "customer_id": data.customer_id,
            "price_id": data.price_id
        })
        return SubscriptionResponse.from_stripe(subscription)
    except stripe.error.CardError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> List[SubscriptionResponse]:
    """List all active subscriptions.
    
    Retrieves a list of all active subscriptions for the organization.
    Inactive or canceled subscriptions are not included in the results.
    
    Args:
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        List[SubscriptionResponse]: List of active subscription details
        
    Raises:
        HTTPException(503): If Stripe service is unavailable
        HTTPException(500): If subscription data cannot be processed
    """
    try:
        subscriptions = stripe.list_subscriptions()
        await event_system.emit("subscriptions.listed", {
            "count": len(subscriptions)
        })
        return [SubscriptionResponse.from_stripe(sub) for sub in subscriptions]
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process subscription data: {str(e)}"
        )

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> SubscriptionResponse:
    """Get details of a specific subscription.
    
    Retrieves detailed information about a subscription including its
    current status, billing period, and associated plan.
    
    Args:
        subscription_id: Unique identifier of the subscription
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        SubscriptionResponse: Detailed subscription information
        
    Raises:
        HTTPException(404): If subscription is not found
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        subscription = stripe.get_subscription(subscription_id)
        await event_system.emit("subscription.retrieved", {
            "subscription_id": subscription_id
        })
        return SubscriptionResponse.from_stripe(subscription)
    except stripe.error.InvalidRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {str(e)}"
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription: {str(e)}"
        )

@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> SubscriptionResponse:
    """Update an existing subscription.
    
    Modifies subscription parameters such as the pricing plan.
    Changes take effect according to the subscription's billing cycle.
    
    Args:
        subscription_id: Unique identifier of the subscription to update
        data: Updated subscription parameters
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        SubscriptionResponse: Updated subscription details
        
    Raises:
        HTTPException(404): If subscription is not found
        HTTPException(400): If update parameters are invalid
        HTTPException(402): If payment is required for the update
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        subscription = stripe.update_subscription(
            subscription_id=subscription_id,
            price_id=data.price_id
        )
        await event_system.emit("subscription.updated", {
            "subscription_id": subscription_id,
            "price_id": data.price_id
        })
        return SubscriptionResponse.from_stripe(subscription)
    except stripe.error.InvalidRequestError as e:
        if "No such subscription" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription not found: {subscription_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.CardError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment required: {str(e)}"
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )

@router.delete("/{subscription_id}", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> SubscriptionResponse:
    """Cancel an existing subscription.
    
    Immediately cancels the subscription and stops future billing.
    Any unused portion of the current billing period may be prorated.
    
    Args:
        subscription_id: Unique identifier of the subscription to cancel
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        SubscriptionResponse: The canceled subscription details
        
    Raises:
        HTTPException(404): If subscription is not found
        HTTPException(400): If subscription cannot be canceled
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        subscription = stripe.cancel_subscription(subscription_id)
        await event_system.emit("subscription.canceled", {
            "subscription_id": subscription_id,
            "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None
        })
        return SubscriptionResponse.from_stripe(subscription)
    except stripe.error.InvalidRequestError as e:
        if "No such subscription" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription not found: {subscription_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    customer_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> List[PaymentMethodResponse]:
    """List all payment methods for a customer.
    
    Retrieves all active payment methods associated with the customer,
    including cards, bank accounts, and other payment types.
    
    Args:
        customer_id: Unique identifier of the customer
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        List[PaymentMethodResponse]: List of payment method details
        
    Raises:
        HTTPException(404): If customer is not found
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        payment_methods = stripe.list_payment_methods(customer_id)
        await event_system.emit("payment_methods.listed", {
            "customer_id": customer_id,
            "count": len(payment_methods)
        })
        return [PaymentMethodResponse.from_stripe(pm) for pm in payment_methods]
    except stripe.error.InvalidRequestError as e:
        if "No such customer" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer not found: {customer_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list payment methods: {str(e)}"
        )

@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    data: PaymentMethodCreate,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> PaymentMethodResponse:
    """Add a new payment method to a customer's account.
    
    Attaches a payment method (card, bank account, etc.) to the customer
    for future payments and subscriptions.
    
    Args:
        data: Payment method details including token and customer ID
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        PaymentMethodResponse: Details of the added payment method
        
    Raises:
        HTTPException(404): If customer is not found
        HTTPException(400): If payment method is invalid
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        payment_method = stripe.attach_payment_method(
            payment_method_id=data.payment_method_id,
            customer_id=data.customer_id
        )
        await event_system.emit("payment_method.added", {
            "customer_id": data.customer_id,
            "payment_method_id": data.payment_method_id,
            "type": payment_method.type
        })
        return PaymentMethodResponse.from_stripe(payment_method)
    except stripe.error.InvalidRequestError as e:
        if "No such customer" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer not found: {data.customer_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment method: {str(e)}"
        )

@router.delete("/payment-methods/{payment_method_id}", response_model=bool)
async def remove_payment_method(
    payment_method_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> bool:
    """Remove a payment method from a customer's account.
    
    Detaches a payment method from the customer, preventing its use
    in future payments. Active subscriptions using this payment method
    may need to be updated.
    
    Args:
        payment_method_id: Unique identifier of the payment method to remove
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        bool: True if the payment method was successfully removed
        
    Raises:
        HTTPException(404): If payment method is not found
        HTTPException(400): If payment method cannot be removed
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        result = stripe.detach_payment_method(payment_method_id)
        await event_system.emit("payment_method.removed", {
            "payment_method_id": payment_method_id
        })
        return result
    except stripe.error.InvalidRequestError as e:
        if "No such payment method" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment method not found: {payment_method_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove payment method: {str(e)}"
        )

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    customer_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> List[InvoiceResponse]:
    """List all invoices for a customer.
    
    Retrieves all invoices associated with the customer, including
    paid, unpaid, and pending invoices. Results are ordered by
    creation date, with the most recent invoices first.
    
    Args:
        customer_id: Unique identifier of the customer
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        List[InvoiceResponse]: List of invoice details
        
    Raises:
        HTTPException(404): If customer is not found
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        invoices = stripe.list_invoices(customer_id)
        await event_system.emit("invoices.listed", {
            "customer_id": customer_id,
            "count": len(invoices),
            "total_amount": sum(inv.amount_due for inv in invoices)
        })
        return [InvoiceResponse.from_stripe(inv) for inv in invoices]
    except stripe.error.InvalidRequestError as e:
        if "No such customer" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer not found: {customer_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list invoices: {str(e)}"
        )

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> InvoiceResponse:
    """Get detailed information about a specific invoice.
    
    Retrieves comprehensive details about an invoice including
    line items, payment status, and associated subscription.
    
    Args:
        invoice_id: Unique identifier of the invoice
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        InvoiceResponse: Detailed invoice information
        
    Raises:
        HTTPException(404): If invoice is not found
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        invoice = stripe.get_invoice(invoice_id)
        await event_system.emit("invoice.retrieved", {
            "invoice_id": invoice_id,
            "amount": invoice.amount_due,
            "status": invoice.status
        })
        return InvoiceResponse.from_stripe(invoice)
    except stripe.error.InvalidRequestError as e:
        if "No such invoice" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice not found: {invoice_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve invoice: {str(e)}"
        )

@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(
    invoice_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> InvoiceResponse:
    """Pay an unpaid invoice.
    
    Attempts to collect payment for an unpaid invoice using the
    customer's default payment method or a specified payment method.
    
    Args:
        invoice_id: Unique identifier of the invoice to pay
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        InvoiceResponse: Updated invoice details after payment
        
    Raises:
        HTTPException(404): If invoice is not found
        HTTPException(400): If invoice cannot be paid
        HTTPException(402): If payment fails
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        invoice = stripe.pay_invoice(invoice_id)
        await event_system.emit("invoice.paid", {
            "invoice_id": invoice_id,
            "amount": invoice.amount_due,
            "status": invoice.status
        })
        return InvoiceResponse.from_stripe(invoice)
    except stripe.error.InvalidRequestError as e:
        if "No such invoice" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice not found: {invoice_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.CardError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment failed: {str(e)}"
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {str(e)}"
        )

@router.post("/portal", response_model=BillingPortalResponse)
async def get_billing_portal(
    customer_id: str,
    return_url: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> BillingPortalResponse:
    """Create a billing portal session for a customer.
    
    Generates a secure URL that allows customers to manage their
    billing settings, including payment methods, subscriptions,
    and invoices.
    
    Args:
        customer_id: Unique identifier of the customer
        return_url: URL to redirect to after the customer completes portal actions
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        BillingPortalResponse: URL to access the billing portal
        
    Raises:
        HTTPException(404): If customer is not found
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        portal = stripe.create_billing_portal(
            customer_id=customer_id,
            return_url=return_url
        )
        await event_system.emit("billing_portal.created", {
            "customer_id": customer_id,
            "return_url": return_url
        })
        return BillingPortalResponse(url=portal.url)
    except stripe.error.InvalidRequestError as e:
        if "No such customer" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer not found: {customer_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create billing portal: {str(e)}"
        )

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    subscription_id: str,
    db: DBSession,
    stripe: StripeClientDep,
    event_system: EventSystemDep
) -> UsageResponse:
    """Get detailed usage information for a subscription.
    
    Retrieves current usage metrics for a metered subscription,
    including consumed quantities and any usage-based charges
    that will appear on the next invoice.
    
    Args:
        subscription_id: Unique identifier of the subscription
        db: Database session
        stripe: Stripe client for payment processing
        event_system: Event system for audit logging
        
    Returns:
        UsageResponse: Current usage metrics and billing details
        
    Raises:
        HTTPException(404): If subscription is not found
        HTTPException(400): If usage cannot be retrieved
        HTTPException(503): If Stripe service is unavailable
    """
    try:
        usage = await stripe.get_subscription_usage(subscription_id)
        await event_system.emit("usage.retrieved", {
            "subscription_id": subscription_id,
            "current_usage": usage.current_usage,
            "limit": usage.limit
        })
        return usage
    except stripe.error.InvalidRequestError as e:
        if "No such subscription" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription not found: {subscription_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage: {str(e)}"
        ) 
