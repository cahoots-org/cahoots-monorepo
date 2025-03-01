"""Organization domain repositories"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .aggregates import Organization
from .events import OrganizationCreated


class OrganizationRepository(ABC):
    """Abstract base class for organization repositories"""

    @abstractmethod
    def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        """Get organization by ID"""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name"""
        pass

    @abstractmethod
    def save(self, organization: Organization) -> None:
        """Save organization aggregate"""
        pass


class EventStoreOrganizationRepository(OrganizationRepository):
    """Event store implementation of organization repository"""

    def __init__(self, event_store):
        self.event_store = event_store

    def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        """Get organization by ID"""
        events = self.event_store.get_events_for_aggregate(organization_id)
        if not events:
            return None

        organization = Organization(organization_id=organization_id)
        for event in events:
            organization.apply_event(event)
        return organization

    def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name"""
        # Get all organization creation events
        events = self.event_store.get_all_events()
        creation_event = next(
            (e for e in events 
             if isinstance(e, OrganizationCreated) and e.name == name),
            None
        )
        if not creation_event:
            return None

        return self.get_by_id(creation_event.organization_id)

    def save(self, organization: Organization) -> None:
        """Save organization aggregate - no-op for event store"""
        # No need to save the aggregate since we're using event sourcing
        pass 