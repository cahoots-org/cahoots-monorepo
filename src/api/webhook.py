"""Webhook endpoints."""
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe.error
from pydantic import BaseModel

from src.database.session import get_session
from src.api.dependencies import EventSystemDep, StripeClientDep, RedisDep
from src.utils.stripe_client import StripeClient
from src.utils.event_system import EventSystem

class WebhookResponse(BaseModel):
    """Webhook response model."""
    status: str

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    event_system: EventSystemDep,
    stripe_client: StripeClientDep,
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
        
        return WebhookResponse(status="success")
        
    finally:
        if event_system:
            await event_system.disconnect() 