"""Security manager composing security components."""
from typing import Optional, Dict, Any
import logging
from fastapi import HTTPException, status

from cahoots_core.utils.config import SecurityConfig
from cahoots_core.utils.infrastructure.redis.client import RedisClient, RedisConfig

from .tokens import JWTTokenProvider, RedisTokenProvider
from .sessions import RedisSessionProvider
from .rbac import RedisRBACProvider, Role, Permission, Action

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security components and operations."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize security manager.
        
        Args:
            config: Security configuration
        """
        self.config = config
        self._redis_client: Optional[RedisClient] = None
        self._token_provider: Optional[RedisTokenProvider] = None
        self._session_provider: Optional[RedisSessionProvider] = None
        self._rbac_provider: Optional[RedisRBACProvider] = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize security services."""
        if self._initialized:
            return
            
        try:
            # Initialize Redis
            logger.info("Initializing Redis client...")
            redis_config = RedisConfig(url=self.config.redis_url)
            self._redis_client = RedisClient(redis_config)
            await self._redis_client.connect()
            
            # Initialize providers
            logger.info("Initializing security providers...")
            jwt_provider = JWTTokenProvider(self.config.secret_key)
            self._token_provider = RedisTokenProvider(self._redis_client, jwt_provider)
            self._session_provider = RedisSessionProvider(self._redis_client, self._token_provider)
            self._rbac_provider = RedisRBACProvider(self._redis_client)
            
            self._initialized = True
            logger.info("Security manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Security initialization failed: {str(e)}"
            )
    
    async def create_session(self, user_id: str, data: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
        """Create a new session.
        
        Args:
            user_id: User ID for session
            data: Optional session data
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        if not self._initialized:
            await self.initialize()
        return await self._session_provider.create_session(user_id, data)
    
    async def end_session(self, session_id: str) -> None:
        """End a session.
        
        Args:
            session_id: Session ID to end
        """
        if not self._initialized:
            await self.initialize()
        await self._session_provider.end_session(session_id)
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a token.
        
        Args:
            token: Token to validate
            
        Returns:
            Decoded token data
        """
        if not self._initialized:
            await self.initialize()
        return await self._token_provider.validate_token(token)
    
    async def revoke_token(self, token: str) -> None:
        """Revoke a token.
        
        Args:
            token: Token to revoke
        """
        if not self._initialized:
            await self.initialize()
        await self._token_provider.revoke_token(token)
    
    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission.
        
        Args:
            user_id: User ID to check
            resource: Resource to check access for
            action: Action to check
            
        Returns:
            True if user has permission
        """
        if not self._initialized:
            await self.initialize()
        return await self._rbac_provider.check_permission(user_id, resource, action)
    
    async def assign_role(self, user_id: str, role_name: str) -> None:
        """Assign role to user.
        
        Args:
            user_id: User ID to assign role to
            role_name: Role to assign
        """
        if not self._initialized:
            await self.initialize()
        await self._rbac_provider.assign_role(user_id, role_name) 