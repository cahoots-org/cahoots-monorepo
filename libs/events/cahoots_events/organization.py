"""Organization domain events"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from .base import Event, EventMetadata


@dataclass
class OrganizationCreated(Event):
    """Event when a new organization is created"""
    organization_id: UUID
    name: str
    description: str
    created_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, name: str, description: str, created_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.name = name
        self.description = description
        self.created_by = created_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationNameUpdated(Event):
    """Event when an organization's name is updated"""
    organization_id: UUID
    old_name: str
    new_name: str
    reason: str
    updated_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, old_name: str, new_name: str, reason: str, updated_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.old_name = old_name
        self.new_name = new_name
        self.reason = reason
        self.updated_by = updated_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationMemberAdded(Event):
    """Event when a member is added to an organization"""
    organization_id: UUID
    user_id: UUID
    role: str
    added_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, user_id: UUID, role: str, added_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role
        self.added_by = added_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationMemberRemoved(Event):
    """Event when a member is removed from an organization"""
    organization_id: UUID
    user_id: UUID
    removed_by: UUID
    reason: Optional[str] = None

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, user_id: UUID, removed_by: UUID, reason: Optional[str] = None):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.user_id = user_id
        self.removed_by = removed_by
        self.reason = reason

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationMemberRoleChanged(Event):
    """Event when a member's role is changed"""
    organization_id: UUID
    user_id: UUID
    old_role: str
    new_role: str
    changed_by: UUID
    reason: str

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, user_id: UUID, old_role: str, new_role: str,
                 changed_by: UUID, reason: str):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role
        self.changed_by = changed_by
        self.reason = reason

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationArchived(Event):
    """Event when an organization is archived"""
    organization_id: UUID
    reason: str
    archived_by: UUID
    archived_at: datetime

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 organization_id: UUID, reason: str, archived_by: UUID, archived_at: datetime):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.reason = reason
        self.archived_by = archived_by
        self.archived_at = archived_at

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id 