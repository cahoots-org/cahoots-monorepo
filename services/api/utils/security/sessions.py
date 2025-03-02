"""Session management module."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from cahoots_core.utils.infrastructure.redis.client import RedisClient

from ..security.base import SessionProvider
from ..security.tokens import RedisTokenProvider


class RedisSessionProvider(SessionProvider):
    """Redis-backed session management."""

    def __init__(
        self,
        redis_client: RedisClient,
        token_provider: RedisTokenProvider,
        access_token_expires: int = 15,  # minutes
        refresh_token_expires: int = 30,  # days
    ):
        """Initialize session provider.

        Args:
            redis_client: Redis client instance
            token_provider: Token provider for session tokens
            access_token_expires: Access token expiration in minutes
            refresh_token_expires: Refresh token expiration in days
        """
        self.redis = redis_client
        self.token_provider = token_provider
        self.access_token_expires = timedelta(minutes=access_token_expires)
        self.refresh_token_expires = timedelta(days=refresh_token_expires)

    async def create_session(
        self, user_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Create a new session with access and refresh tokens.

        Args:
            user_id: User ID for the session
            data: Optional additional session data

        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Create access token
        access_token = await self.token_provider.create_token(
            data={"sub": user_id, "type": "access"}, expires_in=self.access_token_expires
        )

        # Create refresh token
        refresh_token = await self.token_provider.create_token(
            data={"sub": user_id, "type": "refresh"}, expires_in=self.refresh_token_expires
        )

        # Store session data
        session_id = secrets.token_urlsafe()
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            **(data or {}),
        }

        await self.redis.setex(
            f"session:{session_id}", self.refresh_token_expires.total_seconds(), session_data
        )

        # Store refresh token mapping
        await self.redis.setex(
            f"refresh_token:{refresh_token}", self.refresh_token_expires.total_seconds(), user_id
        )

        return access_token, refresh_token

    async def end_session(self, session_id: str) -> None:
        """End a session.

        Args:
            session_id: Session ID to end
        """
        # Delete session data
        await self.redis.delete(f"session:{session_id}")

        # Note: We don't revoke tokens here since they'll expire naturally
        # and revocation is handled by RedisTokenProvider
