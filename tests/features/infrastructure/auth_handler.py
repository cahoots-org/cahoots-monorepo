"""Authentication handler for tests"""
from datetime import datetime
from typing import List
from uuid import UUID, uuid4
import hashlib
import secrets

from ..test_imports import EventMetadata
from ..infrastructure.repository import UserRepository
from ..infrastructure.notifications import MockEmailService

# Stub class definitions for commands that are imported
class RegisterUser:
    def __init__(self, command_id, correlation_id, email, password, name):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email
        self.password = password
        self.name = name

class VerifyEmail:
    def __init__(self, command_id, correlation_id, user_id, verification_token):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.verification_token = verification_token

class LoginUser:
    def __init__(self, command_id, correlation_id, email, password):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email
        self.password = password

class RequestPasswordReset:
    def __init__(self, command_id, correlation_id, email):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email

class ResetPassword:
    def __init__(self, command_id, correlation_id, user_id, reset_token, new_password):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.reset_token = reset_token
        self.new_password = new_password

class RefreshToken:
    def __init__(self, command_id, correlation_id, user_id, refresh_token):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.refresh_token = refresh_token

class LogoutUser:
    def __init__(self, command_id, correlation_id, user_id, session_id):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id

class RevokeSession:
    def __init__(self, command_id, correlation_id, user_id, session_id):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id

# Stub class definitions for events that are imported
class UserRegistered:
    def __init__(self, event_id, timestamp, metadata, user_id, email, name, password_hash):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.email = email
        self.name = name
        self.password_hash = password_hash

class EmailVerified:
    def __init__(self, event_id, timestamp, metadata, user_id, verification_token):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.verification_token = verification_token

class UserLoggedIn:
    def __init__(self, event_id, timestamp, metadata, user_id, session_id, access_token, refresh_token):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.session_id = session_id
        self.access_token = access_token
        self.refresh_token = refresh_token

class PasswordResetRequested:
    def __init__(self, event_id, timestamp, metadata, user_id, reset_token):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.reset_token = reset_token

class PasswordReset:
    def __init__(self, event_id, timestamp, metadata, user_id, password_hash):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.password_hash = password_hash

class TokenRefreshed:
    def __init__(self, event_id, timestamp, metadata, user_id, access_token, refresh_token):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token

class UserLoggedOut:
    def __init__(self, event_id, timestamp, metadata, user_id, session_id):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.session_id = session_id

class SessionRevoked:
    def __init__(self, event_id, timestamp, metadata, user_id, session_id):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.user_id = user_id
        self.session_id = session_id

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
        # Stub implementation for tests
        return [{'user_id': uuid4()}]

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

    def handle_login(self, cmd: LoginUser) -> List[UserLoggedIn]:
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

        # For testing, just generate a new access token without checking for the session
        # In a real implementation, we would find the session by refresh token
        new_access_token = secrets.token_urlsafe(32)
        
        # Update the user's sessions if needed
        if hasattr(user, 'sessions'):
            for session_id, session_data in user.sessions.items():
                if session_data.get('refresh_token') == cmd.refresh_token:
                    session_data['access_token'] = new_access_token
                    
            self.user_repository.save_user(user)
        
        # Create the event
        event = TokenRefreshed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            access_token=new_access_token,
            refresh_token=cmd.refresh_token
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event]

    def handle_logout(self, cmd: LogoutUser) -> List[UserLoggedOut]:
        """Handle Logout command"""
        user = self.user_repository.get_by_id(cmd.user_id)
        if not user:
            raise ValueError(f"No user found with id {cmd.user_id}")

        # For testing, just create a logout event without verifying the session
        # Revoke the session in the user object
        if hasattr(user, 'revoke_session'):
            user.revoke_session(cmd.session_id)
            self.user_repository.save_user(user)

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

        # For testing, just create a revoke event without verifying the session
        # Revoke the session in the user object if it exists
        if hasattr(user, 'revoke_session'):
            user.revoke_session(cmd.session_id)
            self.user_repository.save_user(user)

        event = SessionRevoked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            user_id=cmd.user_id,
            session_id=cmd.session_id
        )

        self.event_store.append_events(cmd.user_id, [event])
        return [event] 