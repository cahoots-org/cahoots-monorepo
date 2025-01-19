"""API dependencies."""
from typing import AsyncGenerator, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)

from cahoots_core.utils.config import get_settings
from cahoots_events.bus.system import EventSystem, get_event_system
from cahoots_core.utils.db import get_shared_session
from cahoots_core.services.stripe import get_stripe_client
from cahoots_core.utils.redis import get_redis_client
from cahoots_core.utils.security import SecurityManager
from cahoots_core.utils.config import SecurityConfig

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    logger.debug("Getting database session")
    try:
        async for session in get_shared_session():
            logger.debug("Successfully got database session")
            yield session
    except Exception as e:
        logger.error("Failed to get database session: %s", str(e), exc_info=True)
        raise

async def get_verified_redis() -> Redis:
    """Get verified Redis client.
    
    Returns:
        Redis: Verified Redis client
        
    Raises:
        HTTPException: If Redis connection fails
    """
    logger.debug("Getting Redis client")
    try:
        redis = await get_redis_client()
        await redis.ping()  # Verify connection
        logger.debug("Successfully verified Redis connection")
        return redis
    except Exception as e:
        logger.error("Failed to get Redis client: %s", str(e), exc_info=True)
        raise

async def get_verified_event_system(
    redis: Redis = Depends(get_verified_redis)
) -> EventSystem:
    """Get verified event system.
    
    Args:
        redis: Redis client
        
    Returns:
        EventSystem: Verified event system
        
    Raises:
        HTTPException: If event system connection fails
    """
    logger.debug("Getting event system")
    try:
        event_system = await get_event_system()
        await event_system.verify_connection()
        logger.debug("Successfully verified event system connection")
        return event_system
    except Exception as e:
        logger.error("Failed to get event system: %s", str(e), exc_info=True)
        raise 

async def get_security_manager(
    redis: Redis = Depends(get_verified_redis)
) -> SecurityManager:
    """Get security manager instance.
    
    Args:
        redis: Redis client
        
    Returns:
        SecurityManager: Security manager instance
        
    Raises:
        HTTPException: If security manager initialization fails
    """
    logger.debug("Getting security manager")
    try:
        config = SecurityConfig()
        security_manager = SecurityManager(redis=redis, config=config)
        logger.debug("Successfully initialized security manager")
        return security_manager
    except Exception as e:
        logger.error("Failed to initialize security manager: %s", str(e), exc_info=True)
        raise 