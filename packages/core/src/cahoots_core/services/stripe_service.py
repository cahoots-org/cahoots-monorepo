"""Stripe service implementation."""
from typing import List, Optional, Dict, Any
from fastapi import Depends
from src.utils.config import get_settings
from src.utils.infrastructure import StripeClient, get_stripe_client

def get_stripe_service() -> StripeClient:
    """Get Stripe client instance.
    
    Returns:
        StripeClient: Configured Stripe client
    """
    settings = get_settings()
    return get_stripe_client(settings.stripe_api_key) 