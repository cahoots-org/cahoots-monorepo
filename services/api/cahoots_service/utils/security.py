"""Security utilities."""
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
import secrets
from enum import Enum
from dataclasses import dataclass
import logging
import asyncio
from redis.asyncio import Redis

from libs.core.cahoots_core.models.api_key import APIKey
from libs.core.cahoots_core.utils.config.base import SecurityConfig
from libs.core.cahoots_core.utils.infrastructure.redis.client import RedisClient, RedisConfig
from libs.core.cahoots_core.utils.infrastructure.redis.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ResourceType(str, Enum):
    """Types of resources that can have permissions."""
    PROJECT = "project"
    ORGANIZATION = "organization"
    TEAM = "team"
    USER = "user"

class PermissionLevel(str, Enum):
    """Permission levels with implicit inheritance."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

    def __ge__(self, other: 'PermissionLevel') -> bool:
        """Check if this permission level includes another."""
        levels = {
            self.READ: 1,
            self.WRITE: 2,
            self.ADMIN: 3
        }
        return levels[self] >= levels[other]

@dataclass
class Permission:
    """Permission definition."""
    resource_type: ResourceType
    level: PermissionLevel
    resource_id: Optional[str] = None

@dataclass
class Role:
    """Role definition with associated permissions."""
    name: str
    permissions: List[Permission]
    description: Optional[str] = None

class RoleManager:
    """Manager for role-based access control."""

    def __init__(self):
        """Initialize role manager."""
        self._roles: Dict[str, Role] = {}
        self.logger = logging.getLogger(__name__)

    async def create_role(self, role: Role) -> None:
        """Create a new role with permissions.
        
        Args:
            role: Role to create
        """
        if role.name in self._roles:
            raise ValueError(f"Role {role.name} already exists")
        
        self._roles[role.name] = role
        self.logger.info(f"Created role {role.name} with {len(role.permissions)} permissions")

    async def get_role_permissions(self, role_name: str) -> List[Permission]:
        """Get permissions for a role.
        
        Args:
            role_name: Name of the role
            
        Returns:
            List of permissions for the role
            
        Raises:
            ValueError: If role doesn't exist
        """
        if role_name not in self._roles:
            raise ValueError(f"Role {role_name} does not exist")
        
        return self._roles[role_name].permissions

    async def check_permission(
        self,
        role_name: str,
        required_permission: Permission
    ) -> bool:
        """Check if a role has a specific permission.
        
        Args:
            role_name: Name of the role
            required_permission: Permission to check
            
        Returns:
            True if role has the permission, False otherwise
        """
        if role_name not in self._roles:
            return False
            
        role_permissions = self._roles[role_name].permissions
        
        for permission in role_permissions:
            # Check resource type matches
            if permission.resource_type != required_permission.resource_type:
                continue
                
            # Check resource ID if specified
            if (permission.resource_id and required_permission.resource_id and 
                permission.resource_id != required_permission.resource_id):
                continue
                
            # Check permission level (with inheritance)
            if permission.level >= required_permission.level:
                return True
                
        return False

    async def update_role(self, role_name: str, permissions: List[Permission]) -> None:
        """Update permissions for an existing role.
        
        Args:
            role_name: Name of the role to update
            permissions: New permissions for the role
            
        Raises:
            ValueError: If role doesn't exist
        """
        if role_name not in self._roles:
            raise ValueError(f"Role {role_name} does not exist")
            
        role = self._roles[role_name]
        role.permissions = permissions
        self.logger.info(f"Updated role {role_name} with {len(permissions)} permissions")

@dataclass
class SecurityPolicy:
    """Security policy definition."""
    name: str
    rules: Dict[str, Any]
    description: Optional[str] = None
    extends: Optional[str] = None

class PolicyManager:
    """Manager for security policy enforcement."""

    def __init__(self):
        """Initialize policy manager."""
        self._policies: Dict[str, SecurityPolicy] = {}
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter()

    async def create_policy(self, policy: SecurityPolicy, ttl: Optional[int] = None) -> None:
        """Create a new security policy.
        
        Args:
            policy: Policy to create
            ttl: Time-to-live in seconds (optional)
            
        Raises:
            ValueError: If policy with same name exists
        """
        if policy.name in self._policies:
            raise ValueError(f"Policy {policy.name} already exists")
            
        self._policies[policy.name] = policy
        self.logger.info(f"Created policy {policy.name} with rules: {policy.rules}")

    async def get_policy(self, policy_name: str) -> Optional[SecurityPolicy]:
        """Get a policy by name.
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Policy if found, None otherwise
        """
        return self._policies.get(policy_name)

    async def validate_key_usage(self, key_name: str, data: Dict[str, Any]) -> bool:
        """Validate key usage against applicable policies.
        
        Args:
            key_name: Name of the key to validate
            data: Data to validate against policies
            
        Returns:
            True if validation passes, False otherwise
        """
        # Get all applicable policies
        policies = self._get_applicable_policies(data)
        
        # No policies means no restrictions
        if not policies:
            return True
            
        # Validate against each policy
        for policy in policies:
            if not self._validate_against_policy(policy, data):
                self.logger.warning(f"Key {key_name} failed validation against policy {policy.name}")
                return False
                
        return True

    def _get_applicable_policies(self, data: Dict[str, Any]) -> List[SecurityPolicy]:
        """Get all policies that apply to the given data.
        
        Args:
            data: Data to check policies against
            
        Returns:
            List of applicable policies
        """
        applicable = []
        for policy in self._policies.values():
            # Check if policy extends another
            if policy.extends:
                base_policy = self._policies.get(policy.extends)
                if base_policy:
                    # Merge rules with base policy
                    merged_rules = {**base_policy.rules}
                    merged_rules.update(policy.rules)
                    policy.rules = merged_rules
                    
            applicable.append(policy)
            
        return applicable

    def _validate_against_policy(self, policy: SecurityPolicy, data: Dict[str, Any]) -> bool:
        """Validate data against a single policy.
        
        Args:
            policy: Policy to validate against
            data: Data to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        for rule_type, rule_value in policy.rules.items():
            if rule_type == "ip_whitelist" and "client_ip" in data:
                if data["client_ip"] not in rule_value:
                    return False
                    
            elif rule_type == "allowed_hours" and "request_hour" in data:
                if data["request_hour"] not in rule_value:
                    return False
                    
            elif rule_type == "required_scopes" and "scopes" in data:
                if not all(scope in data["scopes"] for scope in rule_value):
                    return False
                    
            elif rule_type == "rate_limit":
                # Rate limiting handled by RateLimiter class
                pass
                
            elif rule_type == "resource_access":
                for resource_type, allowed_values in rule_value.items():
                    if resource_type in data and data[resource_type] not in allowed_values:
                        return False
                        
            elif rule_type == "allowed_orgs" and "organization" in data:
                if data["organization"] not in rule_value:
                    return False
                    
            elif rule_type == "time_window" and "request_time" in data:
                try:
                    request_time = datetime.strptime(data["request_time"], "%H:%M").time()
                    start_time = datetime.strptime(rule_value["start"], "%H:%M").time()
                    end_time = datetime.strptime(rule_value["end"], "%H:%M").time()
                    
                    if not (start_time <= request_time <= end_time):
                        return False
                except (ValueError, KeyError):
                    return False
                    
        return True

class TokenManager:
    """Manager for token lifecycle and session management."""

    def __init__(self, redis_client, config: SecurityConfig):
        """Initialize token manager.
        
        Args:
            redis_client: Redis client instance
            config: Security configuration
        """
        self.redis = redis_client
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def create_access_token(
        self,
        data: Dict[str, Any],
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Create a new access token.
        
        Args:
            data: Token payload data
            expires_in: Optional custom expiration time
            
        Returns:
            Generated JWT token
        """
        to_encode = data.copy()
        expire_time = expires_in or timedelta(minutes=self.config.access_token_expire_minutes)
        to_encode["exp"] = datetime.utcnow() + expire_time
        
        token = jwt.encode(
            to_encode,
            self.config.jwt_secret,
            algorithm=self.config.jwt_algorithm
        )
        
        return token

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode a token.
        
        Args:
            token: Token to validate
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or revoked
        """
        try:
            # Check if token is revoked
            if await self.is_token_revoked(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    async def refresh_token(self, token: str) -> str:
        """Create new token with same data but new expiration.
        
        Args:
            token: Token to refresh
            
        Returns:
            New token
            
        Raises:
            HTTPException: If token is invalid
        """
        # Validate old token
        payload = await self.validate_token(token)
        
        # Remove old expiration
        if "exp" in payload:
            del payload["exp"]
            
        # Create new token
        return await self.create_access_token(payload)

    async def revoke_token(self, token: str) -> None:
        """Revoke a token.
        
        Args:
            token: Token to revoke
        """
        await self.redis.setex(
            f"revoked_token:{token}",
            timedelta(days=7).total_seconds(),  # Keep revocation record for 7 days
            "1"
        )

    async def is_token_revoked(self, token: str) -> bool:
        """Check if a token has been revoked.
        
        Args:
            token: Token to check
            
        Returns:
            True if token is revoked, False otherwise
        """
        return bool(await self.redis.get(f"revoked_token:{token}"))

    async def create_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        expires_in: timedelta
    ) -> None:
        """Create a new session.
        
        Args:
            session_id: Session identifier
            data: Session data
            expires_in: Session expiration time
        """
        # Create access token for session
        access_token = await self.create_access_token(data, expires_in)
        
        # Store session data with token
        session_data = {
            **data,
            "access_token": access_token,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.setex(
            f"session:{session_id}",
            expires_in.total_seconds(),
            session_data
        )

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if exists, None otherwise
        """
        return await self.redis.get(f"session:{session_id}")

    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Update session data.
        
        Args:
            session_id: Session identifier
            data: New session data
        """
        # Get existing session TTL
        ttl = await self.redis.ttl(f"session:{session_id}")
        if ttl > 0:
            await self.redis.setex(
                f"session:{session_id}",
                ttl,
                data
            )

    async def end_session(self, session_id: str) -> None:
        """End a session.
        
        Args:
            session_id: Session identifier
        """
        await self.redis.delete(f"session:{session_id}")

    def verify_permissions(self, token: str, required_permissions: List[str]) -> bool:
        """Verify token has required permissions.
        
        Args:
            token: Token to verify
            required_permissions: List of required permissions
            
        Returns:
            True if token has all required permissions, False otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            token_permissions = payload.get("permissions", [])
            return all(perm in token_permissions for perm in required_permissions)
            
        except jwt.InvalidTokenError:
            return False

class SecurityManager:
    """Manager for security operations."""

    def __init__(self, config: SecurityConfig):
        """Initialize security manager.
        
        Args:
            config: Security configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._redis_client = None
        self._initialized = False
        self.token_manager = None

    async def initialize(self) -> None:
        """Initialize security services."""
        if self._initialized:
            return
            
        try:
            # Initialize Redis client using our own config
            self.logger.info("[SECURITY] Initializing Redis client with URL: %s", self.config.redis_url)
            redis_config = RedisConfig(url=self.config.redis_url)
            self._redis_client = RedisClient(redis_config)
            
            # Connect to Redis
            self.logger.info("[SECURITY] Connecting to Redis...")
            await self._redis_client.connect()
            
            # Verify connection with retries
            await self._verify_redis_health()
            
            # Initialize token manager with the Redis client
            self.logger.info("[SECURITY] Initializing token manager...")
            self.token_manager = TokenManager(self._redis_client, self.config)
            self.logger.info("[SECURITY] Token manager initialized")
            
            self._initialized = True
            self.logger.info("[SECURITY] Security services initialized successfully")
            
        except Exception as e:
            self.logger.error("[SECURITY] Failed to initialize security services: %s", str(e), exc_info=True)
            self._initialized = False
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize security services: {str(e)}"
            )

    async def _verify_redis_health(self) -> None:
        """Verify Redis connection health with retries."""
        max_retries = 3
        retry_delay = 1
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if await self._redis_client.ping():
                    self.logger.info("[SECURITY] Redis connection healthy")
                    return
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.logger.warning(f"[SECURITY] Health check attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(retry_delay)
                    
        raise ConnectionError(f"Redis health check failed after {max_retries} attempts: {str(last_error)}")

    @property
    def redis_client(self) -> Redis:
        """Get Redis client instance."""
        if not self._initialized or not self._redis_client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security services not initialized"
            )
        return self._redis_client

    async def create_session(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        expires_in: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """Create a new session for a user.
        
        Args:
            user_id: User ID to create session for
            data: Optional session data
            expires_in: Optional session expiration time
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        try:
            # Generate tokens
            access_token = self._generate_token(user_id, is_refresh=False)
            refresh_token = self._generate_token(user_id, is_refresh=True)
            
            # Store refresh token in Redis
            await self.redis_client.set(
                f"refresh_token:{refresh_token}",
                user_id,
                expire=2592000  # 30 days
            )
            
            # Store additional session data if provided
            if data:
                session_id = secrets.token_urlsafe()
                session_data = {
                    "user_id": user_id,
                    **data,
                    "created_at": datetime.utcnow().isoformat()
                }
                await self.redis_client.setex(
                    f"session:{session_id}",
                    expires_in.total_seconds() if expires_in else 2592000,
                    session_data
                )
            
            return access_token, refresh_token
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )

    def _generate_token(self, user_id: str, is_refresh: bool = False) -> str:
        """Generate a JWT token.
        
        Args:
            user_id: User ID to generate token for
            is_refresh: Whether this is a refresh token
            
        Returns:
            Generated JWT token
        """
        expiration = datetime.utcnow() + (
            timedelta(days=30) if is_refresh else timedelta(minutes=15)
        )
        
        payload = {
            "sub": user_id,
            "exp": expiration,
            "type": "refresh" if is_refresh else "access"
        }
        
        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm="HS256"
        )

    async def authenticate(self, api_key: str) -> Dict[str, Any]:
        """Authenticate API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dict containing key data
            
        Raises:
            HTTPException: If key is invalid
        """
        # Hash key for comparison
        hashed_key = self._hash_api_key(api_key)
        
        # Look up key in database
        stmt = select(APIKey).where(
            APIKey.hashed_key == hashed_key,
            APIKey.is_active == True
        )
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key or db_key.is_expired():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
            
        return {
            "key_id": db_key.id,
            "user_id": db_key.user_id,
            "organization_id": db_key.organization_id,
            "scopes": db_key.scopes
        }

    async def create_tokens(self, user_id: str) -> Tuple[str, str]:
        """Create access and refresh tokens."""
        try:
            if not self._initialized:
                await self.initialize()
                
            logger.info("[OAUTH_FLOW] Starting token creation for user", extra={"user_id": user_id})
            
            # Create access token
            logger.info("[OAUTH_FLOW] Creating access token")
            access_token = self._generate_token(user_id, is_refresh=False)
            logger.info("[OAUTH_FLOW] Access token created successfully")
        
            # Create refresh token
            logger.info("[OAUTH_FLOW] Creating refresh token")
            refresh_token = self._generate_token(user_id, is_refresh=True)
            logger.info("[OAUTH_FLOW] Refresh token created successfully")
            
            # Store refresh token in Redis
            logger.info("[OAUTH_FLOW] Storing refresh token in Redis")
            await self._redis_client.setex(
                f"refresh_token:{refresh_token}",
                timedelta(days=30).total_seconds(),
                user_id
            )
            logger.info("[OAUTH_FLOW] Refresh token stored in Redis")
        
            return access_token, refresh_token
            
        except Exception as e:
            logger.error("[OAUTH_FLOW] Failed to create tokens", exc_info=e)
            raise HTTPException(
                status_code=500,
                detail="Failed to create authentication tokens"
            )

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token.
        
        Args:
            token: Token to validate
            
        Returns:
            Dict containing token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    async def revoke_token(self, token: str) -> None:
        """Revoke refresh token.
        
        Args:
            token: Token to revoke
        """
        await self.redis_client.delete(f"refresh_token:{token}")

    async def create_verification_token(self, user_id: str) -> str:
        """Create email verification token.
        
        Args:
            user_id: User ID
            
        Returns:
            Verification token
        """
        token = secrets.token_urlsafe()
        
        # Store token in Redis with expiration
        await self.redis_client.setex(
            f"verify:{token}",
            timedelta(hours=24).total_seconds(),
            user_id
        )
        
        return token

    async def verify_email(self, token: str) -> str:
        """Verify email with token.
        
        Args:
            token: Verification token
            
        Returns:
            User ID associated with token
            
        Raises:
            HTTPException: If token is invalid
        """
        user_id = await self.redis_client.get(f"verify:{token}")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token"
            )
            
        # Delete token after use
        await self.redis_client.delete(f"verify:{token}")
        
        return user_id

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key.
        
        Args:
            api_key: API key to hash
            
        Returns:
            Hashed API key
        """
        # TODO: Implement secure hashing
        return api_key  # Placeholder 