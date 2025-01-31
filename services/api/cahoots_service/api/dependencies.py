"""API dependencies."""
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from cahoots_core.exceptions import ServiceError
from cahoots_core.utils.infrastructure.database.client import get_db_client
from cahoots_core.utils.infrastructure.redis.client import get_redis_client, RedisClient
from cahoots_core.utils.infrastructure.redis.manager import RedisManager
from cahoots_core.utils.infrastructure.database.manager import DatabaseManager
from cahoots_core.utils.infrastructure.k8s.client import KubernetesClient
from cahoots_core.utils.infrastructure.stripe.client import get_stripe_client, StripeClient
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus.system import EventSystem
from cahoots_service.utils.config import get_settings, ServiceConfig
from cahoots_service.utils.security import SecurityManager

logger = logging.getLogger(__name__)

async def get_db() -> AsyncGenerator:
    """Get database session."""
    session = None
    try:
        session = await get_db_client().get_async_session().__aenter__()
        try:
            yield session
        except Exception as e:
            if session:
                await session.rollback()
            raise ServiceError(f"Database error: {str(e)}")
        finally:
            if session:
                try:
                    await session.close()
                except Exception:
                    pass
    except Exception as e:
        if session:
            await session.rollback()
        raise ServiceError(f"Database error: {str(e)}")

async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client.
    
    Yields:
        Redis client with active connection
        
    Raises:
        ServiceError: If Redis connection fails
    """
    client = None
    try:
        client = get_redis_client()
        await client.ping()  # Verify connection
        try:
            yield client
        except Exception as e:
            logger.error("Redis operation failed: %s", str(e))
            raise ServiceError(f"Redis operation failed: {str(e)}")
        finally:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass
    except Exception as e:
        if client:
            try:
                await client.close()
            except Exception:
                pass
        logger.error("Failed to connect to Redis: %s", str(e))
        raise ServiceError("Redis connection failed")

async def get_event_bus(redis: Redis = Depends(get_redis)) -> EventSystem:
    """Get event system.
    
    Args:
        redis: Redis client from dependency injection
        
    Returns:
        Configured event system
        
    Raises:
        ServiceError: If event system connection fails
    """
    try:
        event_system = EventSystem(redis_client=redis)
        await event_system.verify_connection()
        return event_system
    except Exception as e:
        logger.error("Failed to connect to event system: %s", str(e))
        raise ServiceError("Event system connection failed")

async def get_settings_instance() -> ServiceConfig:
    """Get service settings."""
    return get_settings()

async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    return DatabaseManager()

async def get_redis_manager() -> RedisManager:
    """Get Redis manager."""
    return RedisManager()

async def get_k8s_client() -> KubernetesClient:
    """Get Kubernetes client."""
    return KubernetesClient()

async def get_github_service() -> GitHubService:
    """Get GitHub service."""
    return GitHubService()

async def get_security_manager() -> SecurityManager:
    """Get security manager."""
    return SecurityManager()

async def get_stripe_client_instance() -> StripeClient:
    """Get Stripe client."""
    settings = get_settings()
    return get_stripe_client(settings.stripe_api_key)

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    security: SecurityManager = Depends(get_security_manager)
) -> UUID:
    """Verify API key and return user ID."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required"
        )
    try:
        user_id = await security.verify_api_key(x_api_key)
        return user_id
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

class ServiceDeps:
    """Service dependencies."""
    
    def __init__(
        self,
        settings: ServiceConfig = Depends(get_settings_instance),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
        event_bus: EventSystem = Depends(get_event_bus),
        k8s: KubernetesClient = Depends(get_k8s_client),
        github: GitHubService = Depends(get_github_service),
        security: SecurityManager = Depends(get_security_manager)
    ):
        """Initialize service dependencies."""
        self.settings = settings
        self.db = db
        self.redis = redis
        self.event_bus = event_bus
        self.k8s = k8s
        self.github = github
        self.security = security

async def get_organization_id(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID")
) -> UUID:
    """Get organization ID from header."""
    if not x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-ID header is required"
        )
    try:
        return UUID(x_organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format"
        ) 