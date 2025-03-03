"""Authentication domain aggregates"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from ..events import Event
from .events import (
    PasswordChanged,
    PasswordReset,
    PasswordResetRequested,
    SessionRevoked,
    TokenRefreshed,
    UserCreated,
    UserLoggedIn,
    UserLoggedOut,
    UserVerified,
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
    """Aggregate root for users"""

    user_id: UUID
    email: str = ""
    password_hash: str = ""
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    sessions: Dict[UUID, UserSession] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pending_events: List[Event] = field(default_factory=list)

    def apply_event(self, event):
        """Apply an event to update the aggregate state"""
        if isinstance(event, UserCreated):
            self.email = event.email
            self.password_hash = event.password_hash
            self.verification_token = event.verification_token
            self.created_at = event.timestamp
            self.updated_at = event.timestamp

        elif isinstance(event, UserVerified):
            if event.verification_token == self.verification_token:
                self.is_verified = True
                self.verification_token = None
                self.updated_at = event.timestamp
            else:
                raise ValueError("Invalid verification token")

        elif isinstance(event, PasswordChanged):
            self.password_hash = event.password_hash
            self.updated_at = event.timestamp

        elif isinstance(event, UserLoggedIn):
            if not self.is_verified:
                raise ValueError("Email not verified")
            session = UserSession(
                session_id=event.session_id,
                access_token=event.access_token,
                refresh_token=event.refresh_token,
                created_at=event.timestamp,
                last_used_at=event.timestamp,
            )
            self.sessions[event.session_id] = session
            self.updated_at = event.timestamp

        elif isinstance(event, PasswordResetRequested):
            self.reset_token = event.reset_token
            self.updated_at = event.timestamp

        elif isinstance(event, PasswordReset):
            if not self.reset_token or self.reset_token != event.reset_token:
                raise ValueError("Invalid reset token")
            self.password_hash = event.password_hash
            self.reset_token = None
            # Invalidate all sessions on password reset
            for session in self.sessions.values():
                session.is_active = False
            self.updated_at = event.timestamp

        elif isinstance(event, TokenRefreshed):
            # Find session by refresh token
            session = next(
                (s for s in self.sessions.values() if s.refresh_token == event.refresh_token), None
            )
            if session and session.is_active:
                session.access_token = event.access_token
                session.last_used_at = event.timestamp
                self.updated_at = event.timestamp
            else:
                raise ValueError("Invalid or inactive refresh token")

        elif isinstance(event, UserLoggedOut):
            if event.session_id in self.sessions:
                self.sessions[event.session_id].is_active = False
                self.updated_at = event.timestamp

        elif isinstance(event, SessionRevoked):
            if event.session_id in self.sessions:
                self.sessions[event.session_id].is_active = False
                self.updated_at = event.timestamp

    def validate_password(self, password_hash: str) -> bool:
        """Validate a password hash against the stored hash"""
        return self.password_hash == password_hash

    def can_login(self) -> bool:
        """Check if user can log in"""
        return self.is_verified

    def can_reset_password(self, reset_token: str) -> bool:
        """Check if password can be reset with given token"""
        return self.reset_token == reset_token

    def can_refresh_token(self, refresh_token: str) -> bool:
        """Check if token can be refreshed"""
        session = next(
            (s for s in self.sessions.values() if s.refresh_token == refresh_token), None
        )
        return session is not None and session.is_active

    def has_active_session(self, session_id: UUID) -> bool:
        """Check if session is active"""
        session = self.sessions.get(session_id)
        return session is not None and session.is_active

    def get_active_sessions(self) -> List[UserSession]:
        """Get all active sessions"""
        return [s for s in self.sessions.values() if s.is_active]

    def cleanup_expired_sessions(self, max_age: timedelta = timedelta(days=30)):
        """Remove expired sessions"""
        now = datetime.utcnow()
        self.sessions = {
            sid: session
            for sid, session in self.sessions.items()
            if now - session.last_used_at <= max_age
        }
        self.updated_at = datetime.utcnow()

    def clear_pending_events(self):
        """Clear the list of pending events"""
        self.pending_events.clear()
