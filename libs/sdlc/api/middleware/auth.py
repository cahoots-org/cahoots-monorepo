import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 30,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.security = HTTPBearer()

    def create_access_token(self, user_id: str) -> str:
        """Create a new access token"""
        expires = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {"sub": str(user_id), "exp": expires, "type": "access"}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a new refresh token"""
        expires = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode = {"sub": str(user_id), "exp": expires, "type": "refresh"}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Tuple[str, str]:
        """Decode and validate a token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload["sub"], payload["type"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Could not validate token")

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        exempt_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/password-reset/request",
        ]
        return any(path.startswith(exempt) for exempt in exempt_paths)

    async def __call__(self, request: Request, call_next):
        """Authentication middleware"""
        # Check if path is exempt
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        try:
            # Get token from header
            auth = await self.security(request)
            if not auth:
                raise HTTPException(status_code=401, detail="Not authenticated")

            # Decode and validate token
            user_id, token_type = self.decode_token(auth.credentials)

            # Check token type
            if token_type != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")

            # Add user ID to request state
            request.state.user_id = user_id

            # Process request
            response = await call_next(request)

            return response

        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")


class RequireRole:
    """Role requirement decorator"""

    def __init__(self, required_role: str):
        self.required_role = required_role

    async def __call__(self, request: Request):
        """Check if user has required role"""
        user_id = request.state.user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Get user's role from view store
        user_view = request.state.view_store.get_view(user_id, UserView)
        if not user_view:
            raise HTTPException(status_code=404, detail="User not found")

        if user_view.role != self.required_role:
            raise HTTPException(status_code=403, detail=f"Role {self.required_role} required")

        return True
