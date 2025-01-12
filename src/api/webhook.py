"""Webhook endpoints."""
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe.error
from pydantic import BaseModel

from src.api.dependencies import get_verified_event_system, get_stripe_client
from src.event_system import EventSystem

class WebhookResponse(BaseModel):
    """Webhook response model."""
    status: str

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    event_system: EventSystem = Depends(get_verified_event_system),
    stripe_client: stripe = Depends(get_stripe_client),
) -> WebhookResponse:
    """Handle Stripe webhook events.
    
    Args:
        request: FastAPI request
        event_system: Event system instance
        stripe_client: Stripe client instance
        
    Returns:
        Webhook processing status
        
    Raises:
        HTTPException: If webhook signature is invalid or missing
    """
    try:
        # Get the raw request body
        body = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
            
        try:
            event = stripe_client.construct_event(body, signature)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
            
        # Process the event
        await stripe_client.handle_webhook_event(event)
        
        # Map event type to internal event name
        event_mapping = {
            "customer.subscription.created": "subscription_created",
            "customer.subscription.updated": "subscription_updated", 
            "customer.subscription.deleted": "subscription_deleted",
            "invoice.payment_succeeded": "payment_succeeded"
        }
        
        if event.type in event_mapping:
            event_data = event.data.object
            payload = {
                "customer_id": event_data.customer,
            }
            
            if event.type.startswith("customer.subscription"):
                payload["subscription_id"] = event_data.id
                if event.type != "customer.subscription.deleted":
                    payload["plan"] = event_data.plan.id
                payload["status"] = event_data.status
            elif event.type == "invoice.payment_succeeded":
                payload["invoice_id"] = event_data.id
                payload["amount_paid"] = event_data.amount_paid
                payload["subscription_id"] = event_data.subscription
                
            await event_system.publish({
                "type": event_mapping[event.type],
                "payload": payload
            })
        
        return WebhookResponse(status="success")
        
    finally:
        if event_system:
            await event_system.verify_connection() 