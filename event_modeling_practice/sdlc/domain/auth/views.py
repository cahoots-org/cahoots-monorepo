from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import UUID

from ..events import Event
from .events import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)


@dataclass
class UserView:
    user_id: UUID
    email: str = ''
    password_hash: str = ''
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    created_at: str = ''
    updated_at: str = ''

    def apply_event(self, event: Event) -> None:
        """Update view based on events"""
        if isinstance(event, UserRegistered):
            self.email = event.email
            self.password_hash = event.password_hash
            self.verification_token = event.verification_token
            self.created_at = event.timestamp.isoformat()
            self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, EmailVerified):
            if event.verification_token == self.verification_token:
                self.is_verified = True
                self.verification_token = None
                self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, PasswordResetRequested):
            self.reset_token = event.reset_token
            self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, PasswordReset):
            self.password_hash = event.password_hash
            self.reset_token = None
            self.updated_at = event.timestamp.isoformat()


@dataclass
class SessionView:
    user_id: UUID
    active_sessions: List[Dict] = field(default_factory=list)
    valid_refresh_tokens: List[str] = field(default_factory=list)

    def apply_event(self, event: Event) -> None:
        """Update view based on events"""
        if isinstance(event, UserLoggedIn):
            session = {
                'session_id': event.session_id,
                'access_token': event.access_token,
                'refresh_token': event.refresh_token,
                'created_at': event.timestamp.isoformat()
            }
            self.active_sessions.append(session)
            self.valid_refresh_tokens.append(event.refresh_token)

        elif isinstance(event, TokenRefreshed):
            # Update access token for the session with the matching refresh token
            for session in self.active_sessions:
                if session['refresh_token'] == event.refresh_token:
                    session['access_token'] = event.access_token
                    break

        elif isinstance(event, UserLoggedOut):
            # Remove session and its refresh token
            for session in self.active_sessions:
                if session['session_id'] == event.session_id:
                    self.active_sessions.remove(session)
                    self.valid_refresh_tokens.remove(session['refresh_token'])
                    break

        elif isinstance(event, SessionRevoked):
            # Remove specific session and its refresh token
            for session in self.active_sessions:
                if session['session_id'] == event.session_id:
                    self.active_sessions.remove(session)
                    self.valid_refresh_tokens.remove(session['refresh_token'])
                    break

        elif isinstance(event, PasswordReset):
            # Invalidate all sessions when password is reset
            self.active_sessions.clear()
            self.valid_refresh_tokens.clear() 