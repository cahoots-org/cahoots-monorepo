"""Authentication repository implementations"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .auth_aggregates import User
from .auth import UserRegistered


class UserRepository(ABC):
    """Abstract base class for user repositories"""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    def save(self, user: User) -> None:
        """Save user aggregate"""
        pass


class EventStoreUserRepository(UserRepository):
    """Event store implementation of user repository"""

    def __init__(self, event_store):
        self.event_store = event_store

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        events = self.event_store.get_events_for_aggregate(user_id)
        if not events:
            return None

        user = User(user_id=user_id)
        for event in events:
            user.apply_event(event)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        # Get all user registration events
        events = self.event_store.get_all_events()
        registration_event = next(
            (e for e in events 
             if isinstance(e, UserRegistered) and e.email == email),
            None
        )
        if not registration_event:
            return None

        return self.get_by_id(registration_event.user_id)

    def save(self, user: User) -> None:
        """Save user aggregate - no-op for event store"""
        # No need to save the aggregate since we're using event sourcing
        pass 