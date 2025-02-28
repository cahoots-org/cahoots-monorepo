"""Authentication handler for tests"""
from datetime import datetime
from typing import List
from uuid import UUID, uuid4
import hashlib
import secrets

from cahoots_events.auth_commands import (
    RegisterUser, VerifyEmail, LoginUser as Login, RequestPasswordReset,
    ResetPassword, RefreshToken, LogoutUser, RevokeSession
)
from cahoots_events.auth import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)
from cahoots_events.base import EventMetadata
from features.infrastructure.repository import UserRepository
from features.infrastructure.notifications import MockEmailService


class AuthHandler:
    """Handler for authentication-related commands"""

    def __init__(self, event_store, view_store, user_repository: UserRepository, email_service: MockEmailService):
        self.event_store = event_store
        self.view_store = view_store
        self.user_repository = user_repository
        self.email_service = email_service

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def handle_register_user(self, cmd: RegisterUser) -> List[UserRegistered]:
        """Handle RegisterUser command"""
        # Check if email already exists
        existing_user = self.user_repository.get_by_email(cmd.email)
        if existing_user:
            raise ValueError("Email already registered")

        user_id = uuid4()
        verification_token = secrets.token_urlsafe(32)
        password_hash = self._hash_password(cmd.password)

        event = UserRegistered(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user_id,
            email=cmd.email,
            password_hash=password_hash,
            verification_token=verification_token
        )

        # Save the event
        self.event_store.append_events(user_id, [event])

        # Send verification email
        self.email_service.send_verification_email(cmd.email, verification_token)

        return [event]

    def handle_verify_email(self, cmd: VerifyEmail) -> List[EmailVerified]:
        """Handle VerifyEmail command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        if not user.verification_token or user.verification_token != cmd.verification_token:
            raise ValueError("Invalid verification token")

        event = EmailVerified(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            verification_token=cmd.verification_token
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event]

    def handle_login(self, cmd: Login) -> List[UserLoggedIn]:
        """Handle Login command"""
        user = self.user_repository.get_by_email(cmd.email)
        if not user:
            raise ValueError("Invalid credentials")

        # Check password
        password_hash = self._hash_password(cmd.password)
        if not user.validate_password(password_hash):
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
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user.user_id,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token
        )

        self.event_store.append_events(user.user_id, [event])
        return [event]

    def handle_request_password_reset(self, cmd: RequestPasswordReset) -> List[PasswordResetRequested]:
        """Handle RequestPasswordReset command"""
        user = self.user_repository.get_by_email(cmd.email)
        if not user:
            # Don't reveal if user exists, but return empty list
            return []

        reset_token = secrets.token_urlsafe(32)
        event = PasswordResetRequested(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=user.user_id,
            reset_token=reset_token
        )

        # Save the event
        self.event_store.append_events(user.user_id, [event])

        # Send password reset email
        self.email_service.send_password_reset_email(cmd.email, reset_token)

        return [event]

    def handle_reset_password(self, cmd: ResetPassword) -> List[PasswordReset]:
        """Handle ResetPassword command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        if not user.reset_token or user.reset_token != cmd.reset_token:
            raise ValueError("Invalid reset token")

        # Hash the new password
        password_hash = self._hash_password(cmd.new_password)

        event = PasswordReset(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            password_hash=password_hash
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event]

    def handle_refresh_token(self, cmd: RefreshToken) -> List[TokenRefreshed]:
        """Handle RefreshToken command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        # Find session by refresh token
        session = next(
            (s for s in user.sessions if s.get('refresh_token') == cmd.refresh_token),
            None
        )
        if not session:
            raise ValueError("Invalid or expired refresh token")

        access_token = secrets.token_urlsafe(32)
        event = TokenRefreshed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            access_token=access_token,
            refresh_token=cmd.refresh_token
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event]

    def handle_logout(self, cmd: LogoutUser) -> List[UserLoggedOut]:
        """Handle Logout command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        session = next(
            (s for s in user.sessions if s.get('session_id') == cmd.session_id),
            None
        )
        if not session:
            raise ValueError("Invalid or expired session")

        event = UserLoggedOut(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event]

    def handle_revoke_session(self, cmd: RevokeSession) -> List[SessionRevoked]:
        """Handle RevokeSession command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        session = next(
            (s for s in user.sessions if s.get('session_id') == cmd.session_id),
            None
        )
        if not session:
            raise ValueError("Invalid or expired session")

        event = SessionRevoked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event] 