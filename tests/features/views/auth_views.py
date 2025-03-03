"""
Authentication view classes for tests
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID


class UserView:
    """User view for authentication"""

    def __init__(self, entity_id=None):
        self.user_id = entity_id
        self.email = None
        self.name = None
        self.is_active = True
        self.is_verified = False
        self.password_hash = None
        self.verification_token = None
        self.reset_token = None
        self.sessions = []
        self.created_at = None

    def apply_event(self, event):
        """Apply an event to update this view"""
        event_type = event.__class__.__name__

        # Handle user registered
        if event_type == "UserRegistered":
            self.email = event.email
            self.name = event.name
            self.password_hash = event.password_hash
            self.verification_token = event.verification_token
            self.created_at = event.timestamp

        # Handle email verified
        elif event_type == "EmailVerified":
            self.is_verified = True
            self.verification_token = None

        # Handle user logged in
        elif event_type == "UserLoggedIn":
            self.sessions.append(
                {
                    "session_id": event.session_id,
                    "access_token": event.access_token,
                    "refresh_token": event.refresh_token,
                    "created_at": event.timestamp,
                    "is_active": True,
                }
            )

        # Handle password reset requested
        elif event_type == "PasswordResetRequested":
            self.reset_token = event.reset_token

        # Handle password reset
        elif event_type == "PasswordReset":
            self.password_hash = event.password_hash
            self.reset_token = None
            # Invalidate all sessions
            for session in self.sessions:
                session["is_active"] = False

        # Handle token refreshed
        elif event_type == "TokenRefreshed":
            for session in self.sessions:
                if session.get("refresh_token") == event.refresh_token:
                    session["access_token"] = event.access_token

        # Handle user logged out
        elif event_type == "UserLoggedOut":
            for session in self.sessions:
                if session.get("session_id") == event.session_id:
                    session["is_active"] = False

        # Handle session revoked
        elif event_type == "SessionRevoked":
            for session in self.sessions:
                if session.get("session_id") == event.session_id:
                    session["is_active"] = False


class SessionView:
    """Session view for authentication"""

    def __init__(self, entity_id=None):
        self.session_id = entity_id
        self.user_id = None
        self.access_token = None
        self.refresh_token = None
        self.created_at = None
        self.last_used_at = None
        self.is_active = True
        self.device_info = None

    def apply_event(self, event):
        """Apply an event to update this view"""
        event_type = event.__class__.__name__

        # Handle user logged in
        if event_type == "UserLoggedIn" and event.session_id == self.session_id:
            self.user_id = event.user_id
            self.access_token = event.access_token
            self.refresh_token = event.refresh_token
            self.created_at = event.timestamp
            self.last_used_at = event.timestamp
            self.is_active = True

        # Handle token refreshed
        elif event_type == "TokenRefreshed" and self.user_id == event.user_id:
            if self.refresh_token == event.refresh_token:
                self.access_token = event.access_token
                self.last_used_at = event.timestamp

        # Handle user logged out
        elif event_type == "UserLoggedOut" and self.session_id == event.session_id:
            self.is_active = False

        # Handle session revoked
        elif event_type == "SessionRevoked" and self.session_id == event.session_id:
            self.is_active = False

        # Handle password reset
        elif event_type == "PasswordReset" and self.user_id == event.user_id:
            self.is_active = False
