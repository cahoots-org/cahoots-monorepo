from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
import httpx
import json
import logging
from uuid import UUID

router = APIRouter()
logger = logging.getLogger(__name__)

class WebhookSubscription(BaseModel):
    """Webhook subscription model"""
    url: HttpUrl
    event_types: List[str]
    secret: str
    description: Optional[str] = None

class WebhookDelivery(BaseModel):
    """Webhook delivery model"""
    webhook_id: UUID
    event_type: str
    payload: Dict
    status: str
    response: Optional[Dict] = None
    error: Optional[str] = None

class WebhookManager:
    """Manages webhook subscriptions and deliveries"""
    
    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store
        self.http_client = httpx.AsyncClient()

    async def deliver_webhook(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        payload: Dict,
        background_tasks: BackgroundTasks
    ):
        """Deliver webhook in the background"""
        background_tasks.add_task(
            self._deliver_webhook,
            subscription,
            event_type,
            payload
        )

    async def _deliver_webhook(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        payload: Dict
    ):
        """Actually deliver the webhook"""
        try:
            # Add webhook signature
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Event': event_type,
                'X-Webhook-Signature': self._generate_signature(
                    payload,
                    subscription.secret
                )
            }
            
            # Make the request
            response = await self.http_client.post(
                str(subscription.url),
                json=payload,
                headers=headers,
                timeout=10.0
            )
            
            # Record delivery
            delivery = WebhookDelivery(
                webhook_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status='success' if response.is_success else 'failed',
                response=response.json() if response.is_success else None,
                error=str(response.text) if not response.is_success else None
            )
            
            # Store delivery record
            await self._store_delivery(delivery)
            
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            # Record failed delivery
            delivery = WebhookDelivery(
                webhook_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status='failed',
                error=str(e)
            )
            await self._store_delivery(delivery)

    def _generate_signature(self, payload: Dict, secret: str) -> str:
        """Generate webhook signature"""
        import hmac
        import hashlib
        
        # Convert payload to string
        payload_str = json.dumps(payload, sort_keys=True)
        
        # Generate HMAC
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    async def _store_delivery(self, delivery: WebhookDelivery):
        """Store webhook delivery record"""
        # TODO: Implement storage of webhook deliveries
        pass

# Router endpoints

@router.post("/subscriptions")
async def create_subscription(
    subscription: WebhookSubscription,
    request: Request
):
    """Create a new webhook subscription"""
    # TODO: Store subscription in event store
    return {"message": "Subscription created"}

@router.get("/subscriptions")
async def list_subscriptions(request: Request):
    """List webhook subscriptions"""
    # TODO: Get subscriptions from view store
    return {"subscriptions": []}

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: UUID,
    request: Request
):
    """Delete a webhook subscription"""
    # TODO: Delete subscription
    return {"message": "Subscription deleted"}

@router.get("/deliveries")
async def list_deliveries(request: Request):
    """List webhook deliveries"""
    # TODO: Get deliveries from view store
    return {"deliveries": []} 