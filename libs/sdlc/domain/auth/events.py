"""Authentication domain events"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..events import Event, EventMetadata


@dataclass
class UserCreated(Event):
    """Event when a user is created"""

    user_id: UUID
    email: str
    password_hash: str
    verification_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        email: str,
        password_hash: str,
        verification_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.verification_token = verification_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class UserVerified(Event):
    """Event when a user is verified"""

    user_id: UUID
    verification_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        verification_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.verification_token = verification_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class PasswordChanged(Event):
    """Event when a password is changed"""

    user_id: UUID
    password_hash: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        password_hash: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.password_hash = password_hash

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class UserLoggedIn(Event):
    """Event when a user logs in"""

    user_id: UUID
    session_id: UUID
    access_token: str
    refresh_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        session_id: UUID,
        access_token: str,
        refresh_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.session_id = session_id
        self.access_token = access_token
        self.refresh_token = refresh_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class PasswordResetRequested(Event):
    """Event when a password reset is requested"""

    user_id: UUID
    reset_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        reset_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.reset_token = reset_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class PasswordReset(Event):
    """Event when a password is reset"""

    user_id: UUID
    password_hash: str
    reset_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        password_hash: str,
        reset_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.password_hash = password_hash
        self.reset_token = reset_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class TokenRefreshed(Event):
    """Event when a token is refreshed"""

    user_id: UUID
    session_id: UUID
    access_token: str
    refresh_token: str

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        session_id: UUID,
        access_token: str,
        refresh_token: str,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.session_id = session_id
        self.access_token = access_token
        self.refresh_token = refresh_token

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class UserLoggedOut(Event):
    """Event when a user logs out"""

    user_id: UUID
    session_id: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        session_id: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.session_id = session_id

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id


@dataclass
class SessionRevoked(Event):
    """Event when a session is revoked"""

    user_id: UUID
    session_id: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        user_id: UUID,
        session_id: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.user_id = user_id
        self.session_id = session_id

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.user_id
