"""Webhook endpoints."""
from fastapi import APIRouter, HTTPException
from ..utils.config import config

router = APIRouter()

@router.post("/github")
async def github_webhook(payload: dict) -> dict:
    """Handle GitHub webhook events.
    
    Args:
        payload: Webhook event payload
        
    Returns:
        Response to webhook
        
    Raises:
        HTTPException: If webhook signature is invalid
    """
    try:
        # Verify webhook signature
        if not payload.get("signature") == config.services["github"].api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature"
            )
            
        # Handle the event
        event_type = payload.get("event")
        if event_type == "push":
            # Handle push event
            pass
        elif event_type == "pull_request":
            # Handle PR event
            pass
            
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) 