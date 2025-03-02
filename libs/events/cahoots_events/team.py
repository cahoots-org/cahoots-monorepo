"""Team domain events"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from .base import Event, EventMetadata


@dataclass
class TeamCreated(Event):
    """Event when a new team is created"""

    organization_id: UUID
    team_id: UUID
    name: str
    description: str
    created_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        organization_id: UUID,
        team_id: UUID,
        name: str,
        description: str,
        created_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.organization_id = organization_id
        self.team_id = team_id
        self.name = name
        self.description = description
        self.created_by = created_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id


@dataclass
class TeamMemberAdded(Event):
    """Event when a member is added to a team"""

    team_id: UUID
    member_id: UUID
    role: str
    added_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        team_id: UUID,
        member_id: UUID,
        role: str,
        added_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.team_id = team_id
        self.member_id = member_id
        self.role = role
        self.added_by = added_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id


@dataclass
class TeamMemberRoleChanged(Event):
    """Event when a team member's role is changed"""

    team_id: UUID
    member_id: UUID
    new_role: str
    reason: str
    updated_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        team_id: UUID,
        member_id: UUID,
        new_role: str,
        reason: str,
        updated_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.team_id = team_id
        self.member_id = member_id
        self.new_role = new_role
        self.reason = reason
        self.updated_by = updated_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id


@dataclass
class TeamMemberRemoved(Event):
    """Event when a member is removed from a team"""

    team_id: UUID
    member_id: UUID
    removed_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        team_id: UUID,
        member_id: UUID,
        removed_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.team_id = team_id
        self.member_id = member_id
        self.removed_by = removed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id


@dataclass
class TeamLeadershipTransferred(Event):
    """Event when team leadership is transferred"""

    team_id: UUID
    old_lead_id: UUID
    new_lead_id: UUID
    transferred_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        team_id: UUID,
        old_lead_id: UUID,
        new_lead_id: UUID,
        transferred_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.team_id = team_id
        self.old_lead_id = old_lead_id
        self.new_lead_id = new_lead_id
        self.transferred_by = transferred_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id


@dataclass
class TeamArchived(Event):
    """Event when a team is archived"""

    team_id: UUID
    reason: str
    archived_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        team_id: UUID,
        reason: str,
        archived_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.team_id = team_id
        self.reason = reason
        self.archived_by = archived_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.team_id
