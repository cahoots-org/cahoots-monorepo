"""Authentication domain aggregates"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID

from .auth import (
    EmailVerified,
    PasswordReset,
    PasswordResetRequested,
    SessionRevoked,
    TokenRefreshed,
    UserLoggedIn,
    UserLoggedOut,
    UserRegistered,
)


@dataclass
class UserSession:
    """Value object for user session"""

    session_id: UUID
    access_token: str
    refresh_token: str
    created_at: datetime
    last_used_at: datetime
    is_active: bool = True


@dataclass
class User:
    """User aggregate"""

    user_id: UUID
    email: str = ""
    password_hash: str = ""
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    sessions: List[Dict] = field(default_factory=list)
    pending_events: List = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def validate_password(self, password_hash: str) -> bool:
        """Validate a password hash against the stored hash"""
        return self.password_hash == password_hash

    def apply_event(self, event) -> None:
        """Apply an event to update the aggregate state"""
        if isinstance(event, UserRegistered):
            self.email = event.email
            self.password_hash = event.password_hash
            self.verification_token = event.verification_token
            self.created_at = event.timestamp
            self.updated_at = event.timestamp

        elif isinstance(event, EmailVerified):
            if event.verification_token == self.verification_token:
                self.is_verified = True
                self.verification_token = None
                self.updated_at = event.timestamp
            else:
                raise ValueError("Invalid verification token")

        elif isinstance(event, UserLoggedIn):
            session = {
                "session_id": event.session_id,
                "access_token": event.access_token,
                "refresh_token": event.refresh_token,
            }
            self.sessions.append(session)
            self.updated_at = event.timestamp

        elif isinstance(event, PasswordResetRequested):
            self.reset_token = event.reset_token
            self.updated_at = event.timestamp

        elif isinstance(event, PasswordReset):
            self.password_hash = event.password_hash
            self.reset_token = None
            # Invalidate all sessions
            self.sessions = []
            self.updated_at = event.timestamp

        elif isinstance(event, TokenRefreshed):
            # Update the session with the new access token
            for session in self.sessions:
                if session.get("refresh_token") == event.refresh_token:
                    session["access_token"] = event.access_token
                    break
            self.updated_at = event.timestamp

        elif isinstance(event, UserLoggedOut) or isinstance(event, SessionRevoked):
            # Remove the session
            self.sessions = [s for s in self.sessions if s.get("session_id") != event.session_id]
            self.updated_at = event.timestamp

    def can_login(self) -> bool:
        """Check if user can log in"""
        return self.is_verified

    def can_reset_password(self, reset_token: str) -> bool:
        """Check if password can be reset with given token"""
        return self.reset_token == reset_token

    def can_refresh_token(self, refresh_token: str) -> bool:
        """Check if token can be refreshed"""
        session = next((s for s in self.sessions if s.get("refresh_token") == refresh_token), None)
        return session is not None

    def has_active_session(self, session_id: UUID) -> bool:
        """Check if session is active"""
        session = next((s for s in self.sessions if s.get("session_id") == session_id), None)
        return session is not None

    def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions"""
        return [s for s in self.sessions if s.get("is_active", True)]

    def cleanup_expired_sessions(self, max_age: timedelta = timedelta(days=30)):
        """Remove expired sessions"""
        now = datetime.utcnow()
        self.sessions = [
            s
            for s in self.sessions
            if now - datetime.fromtimestamp(s.get("last_used_at", 0)) < max_age
        ]
        self.updated_at = datetime.utcnow()
