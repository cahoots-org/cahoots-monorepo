from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from .events import (
    OrganizationCreated, OrganizationNameUpdated,
    OrganizationMemberAdded, OrganizationMemberRemoved,
    OrganizationMemberRoleChanged, OrganizationArchived
)


@dataclass
class OrganizationDetailsView:
    """Detailed view of an organization"""
    organization_id: UUID
    name: str = ''
    description: str = ''
    status: str = 'active'
    created_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    member_count: int = 0
    admin_count: int = 0

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, OrganizationCreated):
            self.name = event.name
            self.description = event.description
            self.created_at = event.timestamp
            self.member_count = 1
            self.admin_count = 1

        elif isinstance(event, OrganizationNameUpdated):
            self.name = event.new_name

        elif isinstance(event, OrganizationMemberAdded):
            self.member_count += 1
            if event.role == 'admin':
                self.admin_count += 1

        elif isinstance(event, OrganizationMemberRemoved):
            self.member_count -= 1
            # We need to track role in a separate view to accurately update admin_count

        elif isinstance(event, OrganizationMemberRoleChanged):
            if event.old_role == 'admin':
                self.admin_count -= 1
            if event.new_role == 'admin':
                self.admin_count += 1

        elif isinstance(event, OrganizationArchived):
            self.status = 'archived'
            self.archived_at = event.archived_at


@dataclass
class OrganizationMemberView:
    """View of organization member details"""
    user_id: UUID
    role: str
    added_at: datetime
    added_by: UUID


@dataclass
class OrganizationMembersView:
    """View of organization members"""
    organization_id: UUID
    members: Dict[UUID, OrganizationMemberView] = field(default_factory=dict)
    roles: Dict[str, Set[UUID]] = field(default_factory=lambda: {
        'admin': set(),
        'member': set(),
        'guest': set(),
        'developer': set()
    })

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, OrganizationCreated):
            member = OrganizationMemberView(
                user_id=event.created_by,
                role='admin',
                added_at=event.timestamp,
                added_by=event.created_by
            )
            self.members[event.created_by] = member
            self.roles['admin'].add(event.created_by)

        elif isinstance(event, OrganizationMemberAdded):
            member = OrganizationMemberView(
                user_id=event.user_id,
                role=event.role,
                added_at=event.timestamp,
                added_by=event.added_by
            )
            self.members[event.user_id] = member
            self.roles[event.role].add(event.user_id)

        elif isinstance(event, OrganizationMemberRemoved):
            if event.user_id in self.members:
                old_role = self.members[event.user_id].role
                self.roles[old_role].remove(event.user_id)
                del self.members[event.user_id]

        elif isinstance(event, OrganizationMemberRoleChanged):
            if event.user_id in self.members:
                member = self.members[event.user_id]
                self.roles[member.role].remove(event.user_id)
                member.role = event.new_role
                self.roles[event.new_role].add(event.user_id)


@dataclass
class OrganizationAuditLogEntry:
    """Entry in the organization audit log"""
    timestamp: datetime
    event_type: str
    user_id: UUID
    details: Dict


@dataclass
class OrganizationAuditLogView:
    """Audit log view for organization events"""
    organization_id: UUID
    entries: List[OrganizationAuditLogEntry] = field(default_factory=list)

    def apply_event(self, event):
        """Update view based on events"""
        entry = None

        if isinstance(event, OrganizationCreated):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='organization_created',
                user_id=event.created_by,
                details={
                    'name': event.name,
                    'description': event.description
                }
            )

        elif isinstance(event, OrganizationNameUpdated):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='name_updated',
                user_id=event.updated_by,
                details={
                    'old_name': event.old_name,
                    'new_name': event.new_name,
                    'reason': event.reason
                }
            )

        elif isinstance(event, OrganizationMemberAdded):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='member_added',
                user_id=event.added_by,
                details={
                    'added_user_id': event.user_id,
                    'role': event.role
                }
            )

        elif isinstance(event, OrganizationMemberRemoved):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='member_removed',
                user_id=event.removed_by,
                details={
                    'removed_user_id': event.user_id,
                    'reason': event.reason
                }
            )

        elif isinstance(event, OrganizationMemberRoleChanged):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='member_role_changed',
                user_id=event.changed_by,
                details={
                    'target_user_id': event.user_id,
                    'old_role': event.old_role,
                    'new_role': event.new_role,
                    'reason': event.reason
                }
            )

        elif isinstance(event, OrganizationArchived):
            entry = OrganizationAuditLogEntry(
                timestamp=event.timestamp,
                event_type='organization_archived',
                user_id=event.archived_by,
                details={
                    'reason': event.reason
                }
            )

        if entry:
            self.entries.append(entry) 