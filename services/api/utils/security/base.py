"""Base interfaces for security components."""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict, Optional


class TokenProvider(ABC):
    """Abstract base class for token operations."""

    @abstractmethod
    async def create_token(
        self, data: Dict[str, Any], expires_in: Optional[timedelta] = None
    ) -> str:
        """Create a token."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """Revoke a token."""
        pass


class SessionProvider(ABC):
    """Abstract base class for session management."""

    @abstractmethod
    async def create_session(
        self, user_id: str, data: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """Create a new session returning (access_token, refresh_token)."""
        pass

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """End a session."""
        pass


class AuthorizationProvider(ABC):
    """Abstract base class for authorization."""

    @abstractmethod
    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission."""
        pass

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[str]:
        """Get user's roles."""
        pass
