"""FastAPI dependencies."""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from src.utils.config import settings
from src.db.session import SessionLocal
from src.event_system import EventSystem

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with SessionLocal() as session:
        yield session

def get_stripe_client() -> stripe.stripe_object.StripeObject:
    """Get Stripe client."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe

def get_event_system() -> EventSystem:
    """Get event system."""
    return EventSystem() 