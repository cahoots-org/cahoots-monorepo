"""FastAPI dependency injection module."""
from typing import AsyncGenerator, Optional, Dict, Any, Annotated, ForwardRef
from contextlib import asynccontextmanager
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from functools import wraps, lru_cache
from datetime import datetime
from redis.asyncio import Redis

from src.database.session import get_session
from src.utils.event_system import EventSystem
from src.utils.stripe_client import StripeClient
from src.utils.config import config
from src.utils.security import SecurityManager, SecurityScope
from src.utils.redis_client import get_redis_client
from src.database.database import get_db
from src.database.models import Organization
from src.models.user import User

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# Core dependencies with proper error handling
@lru_cache
def get_base_redis() -> Redis:
    """Get base Redis client with connection pool.
    
    Returns:
        Redis client instance
        
    Note:
        This is an internal function. Use RedisDep instead.
    """
    return get_redis_client()

@lru_cache
def get_base_event_system(redis: Redis = Depends(get_base_redis)) -> EventSystem:
    """Get base EventSystem instance.
    
    Args:
        redis: Redis client
        
    Returns:
        EventSystem instance
        
    Note:
        This is an internal function. Use EventSystemDep instead.
    """
    event_system = EventSystem(redis, service_name=config.service_name)
    return event_system

async def get_verified_redis(redis: Redis = Depends(get_base_redis)) -> Redis:
    """Get Redis client with verified connection.
    
    Args:
        redis: Base Redis client
        
    Returns:
        Verified Redis client
        
    Raises:
        HTTPException: If Redis connection fails
    """
    try:
        await redis.ping()
        return redis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )

async def get_verified_event_system(
    event_system: EventSystem = Depends(get_base_event_system),
    redis: Redis = Depends(get_verified_redis)
) -> EventSystem:
    """Get EventSystem with verified connection.
    
    Args:
        event_system: Base EventSystem instance
        redis: Verified Redis client
        
    Returns:
        Verified EventSystem instance
        
    Raises:
        HTTPException: If EventSystem verification fails
    """
    try:
        if not event_system.is_connected:
            await event_system.connect()
        if not await event_system.verify_connection():
            raise ValueError("Event system verification failed")
        return event_system
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Event system verification failed: {str(e)}"
        )

async def get_stripe_client() -> StripeClient:
    """Get Stripe client instance.
    
    Returns:
        StripeClient: Stripe client instance
        
    Raises:
        HTTPException: If Stripe client initialization fails
    """
    try:
        return StripeClient(api_key=config.stripe.secret_key.get_secret_value())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe client initialization failed: {str(e)}"
        )

# Type aliases for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_verified_redis)]
EventSystemDep = Annotated[EventSystem, Depends(get_verified_event_system)]
StripeClientDep = Annotated[StripeClient, Depends(get_stripe_client)]
SecurityManagerDep = Annotated[SecurityManager, Depends()]

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        HTTPException: If database connection fails
    """
    try:
        async with get_session() as session:
            yield session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

async def get_current_organization(
    db: DBSession,
    api_key: str = Depends(api_key_header)
) -> Organization:
    """Get current organization from API key.
    
    Args:
        db: Database session
        api_key: API key
        
    Returns:
        Organization: Current organization
        
    Raises:
        HTTPException: If organization not found or API key invalid
    """
    from src.api.auth import verify_api_key
    try:
        organization_id = await verify_api_key(api_key, db)
        org = await db.get(Organization, organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return org
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization: {str(e)}"
        )

def require_scope(required_scope: SecurityScope):
    """Decorator to require specific security scope.
    
    Args:
        required_scope: Required security scope
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args,
            security_manager: SecurityManagerDep,
            current_user: User = Depends(get_current_user),
            **kwargs
        ):
            if not await security_manager.check_scope(current_user, required_scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scope {required_scope} not granted"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience dependencies for common scopes
require_read = require_scope(SecurityScope.READ)
require_write = require_scope(SecurityScope.WRITE)
require_admin = require_scope(SecurityScope.ADMIN)
require_system = require_scope(SecurityScope.SYSTEM)

# Common dependencies
CommonDeps = (
    Depends(get_db),
    Depends(get_verified_redis),
    Depends(get_verified_event_system),
    Depends(get_stripe_client)
) 