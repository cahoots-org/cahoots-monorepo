"""Repository implementations for tests"""
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from cahoots_events.auth_aggregates import User


class UserRepository:
    """Repository for user aggregates"""
    
    def __init__(self, event_store):
        """Initialize the repository"""
        self.event_store = event_store
        self._users: Dict[UUID, User] = {}
        self._email_index: Dict[str, UUID] = {}
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID"""
        if user_id in self._users:
            return self._users[user_id]
        
        # Try to load from events
        events = self.event_store.get_events(user_id)
        if not events:
            return None
        
        user = User(user_id=user_id)
        for event in events:
            user.apply_event(event)
        
        # Cache the user
        self._users[user_id] = user
        if user.email:
            self._email_index[user.email] = user_id
        
        return user
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        if email in self._email_index:
            return self.get_by_id(self._email_index[email])
        
        # We need to scan all users
        for user_id, user in self._users.items():
            if user.email == email:
                self._email_index[email] = user_id
                return user
        
        return None
    
    def save_user(self, user: User) -> None:
        """Save a user to the repository"""
        # Save any pending events
        if user.pending_events:
            self.event_store.append_events(user.user_id, user.pending_events)
            user.pending_events = []
        
        # Update cache
        self._users[user.user_id] = user
        if user.email:
            self._email_index[user.email] = user.user_id 