"""Webhook endpoints."""
from typing import Dict, Any
from cahoots_events.bus.system import EventSystem
from api.billing import get_stripe_client
from api.dependencies import get_verified_event_system
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["webhooks"])

class WebhookResponse(BaseModel):
    """Response model for webhook endpoints."""
    status: str = "success"
    message: str = "Webhook processed successfully"

@router.post("/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    event_system: EventSystem = Depends(get_verified_event_system),
    stripe_client = Depends(get_stripe_client)
) -> WebhookResponse:
    """Handle Stripe webhook events.
    
    Args:
        request: The request object containing the webhook payload
        event_system: Event system for processing events
        stripe_client: Stripe client for verifying webhook signatures
        
    Returns:
        WebhookResponse: Success/failure response
        
    Raises:
        HTTPException: If webhook verification fails
    """
    try:
        # Get raw request body
        payload = await request.body()
        
        # Get Stripe signature from headers (case-insensitive)
        sig = next((v for k,v in request.headers.items() if k.lower() == "stripe-signature"), None)
        if not sig:
            raise HTTPException(status_code=400)
            
        # Verify webhook signature
        try:
            event = stripe_client.verify_webhook(payload, sig)
        except Exception as e:
            raise HTTPException(status_code=400)
        
        # Process the event
        await event_system.publish("stripe.webhook", {
            "event_type": event.type,
            "event_id": event.id,
            "data": event.data.object
        })
        
        return WebhookResponse()
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400) 