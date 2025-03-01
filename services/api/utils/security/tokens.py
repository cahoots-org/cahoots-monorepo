"""Token management module."""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import jwt
from fastapi import HTTPException, status

from ..security.base import TokenProvider
from cahoots_core.utils.infrastructure.redis.client import RedisClient

class JWTTokenProvider(TokenProvider):
    """JWT token implementation."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize provider with secret key and algorithm."""
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    async def create_token(
        self, 
        data: Dict[str, Any], 
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Create a JWT token."""
        to_encode = data.copy()
        if expires_in:
            to_encode["exp"] = datetime.utcnow() + expires_in
            
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode a JWT token."""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
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
        """JWT tokens can't be revoked - use Redis for revocation."""
        pass

class RedisTokenProvider(TokenProvider):
    """Redis-backed token provider with revocation support."""
    
    def __init__(self, redis_client: RedisClient, jwt_provider: JWTTokenProvider):
        """Initialize with Redis client and JWT provider."""
        self.redis = redis_client
        self.jwt = jwt_provider
        
    async def create_token(
        self, 
        data: Dict[str, Any], 
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Create a token using JWT provider."""
        return await self.jwt.create_token(data, expires_in)
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate token and check revocation."""
        if await self._is_revoked(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        return await self.jwt.validate_token(token)
    
    async def revoke_token(self, token: str) -> None:
        """Revoke a token by storing in Redis."""
        await self.redis.setex(
            f"revoked_token:{token}",
            timedelta(days=7).total_seconds(),
            "1"
        )
    
    async def _is_revoked(self, token: str) -> bool:
        """Check if token is revoked."""
        return bool(await self.redis.get(f"revoked_token:{token}")) 