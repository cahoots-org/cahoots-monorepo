"""Authentication command handlers"""
from datetime import datetime
from typing import List
from uuid import UUID, uuid4
import hashlib
import secrets

from .auth_commands import (
    RegisterUser, VerifyEmail, LoginUser, RequestPasswordReset,
    ResetPassword, RefreshToken, LogoutUser, RevokeSession
)
from .auth import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)
from .base import EventMetadata
from .auth_repository import UserRepository
from .auth_notifications import EmailService


class AuthHandler:
    """Handler for authentication-related commands"""

    def __init__(self, event_store, view_store, user_repository: UserRepository, email_service: EmailService):
        self.event_store = event_store
        self.view_store = view_store
        self.user_repository = user_repository
        self.email_service = email_service

    def handle_register_user(self, cmd: RegisterUser) -> List[UserRegistered]:
        """Handle RegisterUser command"""
        # Check if email already exists
        existing_user = self.user_repository.get_by_email(cmd.email)
        if existing_user:
            raise ValueError("Email already registered")

        user_id = uuid4()
        verification_token = secrets.token_urlsafe(32)
        password_hash = hashlib.sha256(cmd.password.encode()).hexdigest()

        event = UserRegistered(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=user_id,
            email=cmd.email,
            password_hash=password_hash,
            verification_token=verification_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        # Send verification email
        self.email_service.send_verification_email(cmd.email, verification_token)

        return [event]

    def handle_verify_email(self, cmd: VerifyEmail) -> List[EmailVerified]:
        """Handle VerifyEmail command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        if user.verification_token != cmd.verification_token:
            raise ValueError("Invalid verification token")

        event = EmailVerified(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=cmd.user_id,
            verification_token=cmd.verification_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_login(self, cmd: LoginUser) -> List[UserLoggedIn]:
        """Handle LoginUser command"""
        user = self.user_repository.get_by_email(cmd.email)
        if not user:
            raise ValueError("Invalid credentials")

        # Check password
        password_hash = hashlib.sha256(cmd.password.encode()).hexdigest()
        if password_hash != user.password_hash:
            raise ValueError("Invalid credentials")

        # Check if email is verified
        if not user.is_verified:
            raise ValueError("Email not verified")

        # Create new session
        session_id = uuid4()
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        event = UserLoggedIn(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=user.user_id,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_request_password_reset(self, cmd: RequestPasswordReset) -> List[PasswordResetRequested]:
        """Handle RequestPasswordReset command"""
        user = self.user_repository.get_by_email(cmd.email)
        if not user:
            raise ValueError("User not found")

        reset_token = secrets.token_urlsafe(32)
        event = PasswordResetRequested(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=user.user_id,
            reset_token=reset_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        # Send password reset email
        self.email_service.send_password_reset_email(cmd.email, reset_token)

        return [event]

    def handle_reset_password(self, cmd: ResetPassword) -> List[PasswordReset]:
        """Handle ResetPassword command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        if not user.can_reset_password(cmd.reset_token):
            raise ValueError("Invalid reset token")

        # Hash the new password
        password_hash = hashlib.sha256(cmd.new_password.encode()).hexdigest()

        # Create the password reset event
        event = PasswordReset(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=cmd.user_id,
            password_hash=password_hash
        )

        # Store and apply the event
        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_refresh_token(self, cmd: RefreshToken) -> List[TokenRefreshed]:
        """Handle RefreshToken command"""
        # Find user by refresh token
        events = self.event_store.get_all_events()
        login_event = next(
            (e for e in events 
             if isinstance(e, UserLoggedIn) and e.refresh_token == cmd.refresh_token),
            None
        )
        if not login_event:
            raise ValueError("Invalid refresh token")

        user = self.user_repository.get_by_id(login_event.user_id)
        if not user or not user.can_refresh_token(cmd.refresh_token):
            raise ValueError("Token has been revoked")

        new_access_token = secrets.token_urlsafe(32)
        event = TokenRefreshed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=login_event.user_id,
            access_token=new_access_token,
            refresh_token=cmd.refresh_token
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_logout(self, cmd: LogoutUser) -> List[UserLoggedOut]:
        """Handle Logout command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user or not user.has_active_session(cmd.session_id):
            raise ValueError("Invalid session")

        event = UserLoggedOut(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_revoke_session(self, cmd: RevokeSession) -> List[SessionRevoked]:
        """Handle RevokeSession command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user or not user.has_active_session(cmd.session_id):
            raise ValueError("Invalid session")

        event = SessionRevoked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event] 