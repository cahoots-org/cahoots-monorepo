"""API dependencies."""
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID
import asyncio

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from redis.asyncio import Redis

from cahoots_core.exceptions import ServiceError
from cahoots_core.utils.infrastructure.database.client import get_db_client
from cahoots_core.utils.infrastructure.redis.client import RedisClient, RedisConfig
from cahoots_core.utils.infrastructure.redis.manager import RedisManager
from cahoots_core.utils.infrastructure.database.manager import DatabaseManager
from cahoots_core.utils.infrastructure.k8s.client import KubernetesClient
from cahoots_core.utils.infrastructure.stripe.client import get_stripe_client, StripeClient
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus.system import EventSystem
from utils.config import get_settings, ServiceConfig, SecurityConfig
from utils.security import SecurityManager

logger = logging.getLogger(__name__)

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Global Redis client
_redis_client: Optional[RedisClient] = None

async def get_redis_client() -> RedisClient:
    """Get or create Redis client singleton.
    
    Returns:
        Redis client instance
        
    Raises:
        ServiceError: If Redis connection fails
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            logger.info("[REDIS] Initializing Redis client with URL: %s", settings.redis_url)
            config = RedisConfig(url=settings.redis_url)
            _redis_client = RedisClient(config)
            
            # Explicitly handle connection
            logger.info("[REDIS] Connecting to Redis...")
            await _redis_client.connect()
            
            # Verify connection with retries
            max_retries = 3
            retry_delay = 1
            for attempt in range(max_retries):
                try:
                    await _redis_client.verify_connection()
                    logger.info("[REDIS] Successfully connected to Redis")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error("[REDIS] All connection attempts failed: %s", str(e))
                        raise
                    logger.warning("[REDIS] Connection attempt %d failed, retrying...", attempt + 1)
                    await asyncio.sleep(retry_delay)
                    
        except Exception as e:
            logger.error("[REDIS] Failed to initialize Redis client: %s", str(e))
            _redis_client = None
            raise ServiceError(f"Redis initialization failed: {str(e)}")
            
    return _redis_client

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.
    
    Yields:
        Database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_redis() -> AsyncGenerator[RedisClient, None]:
    """Get Redis client.
    
    Yields:
        Redis client with active connection
        
    Raises:
        ServiceError: If Redis connection fails
    """
    try:
        client = await get_redis_client()
        yield client
    except Exception as e:
        logger.error(f"Redis operation failed: {str(e)}")
        raise ServiceError(f"Redis operation failed: {str(e)}")

async def get_event_bus(redis: RedisClient = Depends(get_redis)) -> EventSystem:
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
        logger.error(f"Failed to connect to event system: {str(e)}")
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

async def get_security_manager(redis: RedisClient = Depends(get_redis)) -> SecurityManager:
    """Get security manager instance.
    
    Args:
        redis: Redis client from dependency injection
    
    Returns:
        Security manager instance
    """
    config = await get_security_config()
    manager = SecurityManager(config=config)
    await manager.initialize()
    return manager

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
        redis: RedisClient = Depends(get_redis),
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

async def get_security_config() -> SecurityConfig:
    """Get security configuration.
    
    Returns:
        Security configuration
    """
    return SecurityConfig(
        redis_url=settings.redis_url,
        secret_key=settings.jwt_secret_key,
        access_token_expire_minutes=settings.auth_token_expire_minutes
    )

async def get_current_user(
    security: SecurityManager = Depends(get_security_manager),
    authorization: str = Header(..., description="Bearer token")
) -> UUID:
    """Get current user from authorization header.
    
    Args:
        security: Security manager from dependency injection
        authorization: Authorization header containing bearer token
        
    Returns:
        User ID
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    try:
        user_id = await security.verify_token(token)
        return user_id
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        ) 