from datetime import datetime
from typing import List
from uuid import UUID, uuid4
import hashlib
import secrets

from .commands import (
    RegisterUser, VerifyEmail, Login, RequestPasswordReset,
    ResetPassword, RefreshToken, Logout, RevokeSession
)
from .events import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)
from ..events import EventMetadata


class AuthHandler:
    """Handler for authentication-related commands"""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store

    def handle_register_user(self, cmd: RegisterUser) -> List[UserRegistered]:
        """Handle RegisterUser command"""
        user_id = uuid4()
        verification_token = secrets.token_urlsafe(32)
        password_hash = hashlib.sha256(cmd.password.encode()).hexdigest()

        event = UserRegistered(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user_id,
            email=cmd.email,
            password_hash=password_hash,
            verification_token=verification_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_verify_email(self, cmd: VerifyEmail) -> List[EmailVerified]:
        """Handle VerifyEmail command"""
        events = self.event_store.get_events_for_aggregate(cmd.user_id)
        if not events:
            raise ValueError(f"No user found with id {cmd.user_id}")

        event = EmailVerified(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            verification_token=cmd.verification_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_login(self, cmd: Login) -> List[UserLoggedIn]:
        """Handle Login command"""
        # Get all user events to find the user by email
        events = self.event_store.get_all_events()
        user_events = [e for e in events if isinstance(e, UserRegistered)]
        
        # Find user by email
        user_event = next((e for e in user_events if e.email == cmd.email), None)
        if not user_event:
            raise ValueError("Invalid credentials")
        
        # Get all events for this user to find the latest password hash
        user_events = self.event_store.get_events_for_aggregate(user_event.user_id)
        password_events = [
            e for e in user_events 
            if isinstance(e, (UserRegistered, PasswordReset))
        ]
        latest_password_event = max(password_events, key=lambda e: e.timestamp)
        
        # Check password
        password_hash = hashlib.sha256(cmd.password.encode()).hexdigest()
        if password_hash != latest_password_event.password_hash:
            raise ValueError("Invalid credentials")
        
        # Check if email is verified
        verify_events = [
            e for e in user_events 
            if isinstance(e, EmailVerified)
        ]
        if not verify_events:
            raise ValueError("Email not verified")

        # Create new session
        session_id = uuid4()
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        event = UserLoggedIn(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user_event.user_id,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_request_password_reset(self, cmd: RequestPasswordReset) -> List[PasswordResetRequested]:
        """Handle RequestPasswordReset command"""
        # Find user by email
        events = self.event_store.get_all_events()
        user_event = next(
            (e for e in events 
             if isinstance(e, UserRegistered) and e.email == cmd.email),
            None
        )
        if not user_event:
            raise ValueError("User not found")

        reset_token = secrets.token_urlsafe(32)
        event = PasswordResetRequested(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user_event.user_id,
            reset_token=reset_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_reset_password(self, cmd: ResetPassword) -> List[PasswordReset]:
        """Handle ResetPassword command"""
        # Get all events for this user
        events = self.event_store.get_events_for_aggregate(cmd.user_id)
        if not events:
            raise ValueError(f"No user found with id {cmd.user_id}")

        # Find the reset request event
        reset_request = next(
            (e for e in events 
             if isinstance(e, PasswordResetRequested) and e.reset_token == cmd.reset_token),
            None
        )
        if not reset_request:
            raise ValueError("Invalid reset token")

        # Hash the new password
        password_hash = hashlib.sha256(cmd.new_password.encode()).hexdigest()

        # Create the password reset event
        event = PasswordReset(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            password_hash=password_hash
        )

        # Store and apply the event
        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_refresh_token(self, cmd: RefreshToken) -> List[TokenRefreshed]:
        """Handle RefreshToken command"""
        # Find the session with this refresh token
        events = self.event_store.get_all_events()
        login_event = next(
            (e for e in events 
             if isinstance(e, UserLoggedIn) and e.refresh_token == cmd.refresh_token),
            None
        )
        if not login_event:
            raise ValueError("Invalid refresh token")

        # Check if token has been revoked
        revoke_events = [
            e for e in events
            if isinstance(e, (UserLoggedOut, SessionRevoked))
            and e.user_id == login_event.user_id
            and e.session_id == login_event.session_id
        ]
        if revoke_events:
            raise ValueError("Token has been revoked")

        new_access_token = secrets.token_urlsafe(32)
        event = TokenRefreshed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=login_event.user_id,
            access_token=new_access_token,
            refresh_token=cmd.refresh_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_logout(self, cmd: Logout) -> List[UserLoggedOut]:
        """Handle Logout command"""
        event = UserLoggedOut(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_revoke_session(self, cmd: RevokeSession) -> List[SessionRevoked]:
        """Handle RevokeSession command"""
        event = SessionRevoked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event] 