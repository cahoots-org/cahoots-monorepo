"""Repository for user authentication."""

from typing import List, Optional
from uuid import UUID

from ...infrastructure.event_store import EventStore
from ...infrastructure.view_store import ViewStore
from .aggregates import User
from .events import (
    PasswordChanged,
    PasswordReset,
    PasswordResetRequested,
    UserCreated,
    UserVerified,
)
from .views import UserView


class UserRepository:
    """Repository for managing user data."""

    def __init__(self, event_store: EventStore, view_store: ViewStore):
        self.event_store = event_store
        self.view_store = view_store

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID."""
        events = self.event_store.get_events_for_aggregate(user_id)
        if not events:
            return None
        user = User(user_id)
        for event in events:
            user.apply_event(event)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        # Search through UserCreated events to find matching email
        all_events = self.event_store.get_all_events()
        for event in all_events:
            if isinstance(event, UserCreated) and event.email == email:
                return self.get_by_id(event.user_id)
        return None

    def save_user(self, user: User) -> None:
        """Save user changes to the event store."""
        for event in user.pending_events:
            self.event_store.append(event)
            # For UserCreated events, pass as initial event when creating view
            if isinstance(event, UserCreated):
                self.view_store.create_view(UserView, event.user_id, initial_event=event)
            else:
                self.view_store.apply_event(event)
        user.clear_pending_events()
