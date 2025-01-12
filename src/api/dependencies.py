"""API dependencies."""
from typing import AsyncGenerator, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from src.utils.config import get_settings
from src.utils.session import SessionLocal
from src.utils.redis import get_redis_client
from src.event_system import EventSystem
from src.api.middleware.security import SecurityManager

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_verified_redis():
    """Get Redis client with verified connection."""
    redis = await get_redis_client()
    try:
        await redis.ping()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )
    return redis

def get_stripe_client():
    """Get Stripe client."""
    stripe.api_key = get_settings().STRIPE_API_KEY
    return stripe

async def get_verified_event_system(redis=Depends(get_verified_redis)):
    """Get event system with verified connection."""
    event_system = EventSystem(redis=redis)
    try:
        await event_system.verify_connection()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Event system connection failed: {str(e)}"
        )
    return event_system

async def get_security_manager(db=Depends(get_db)):
    """Get security manager instance."""
    return SecurityManager(db) 