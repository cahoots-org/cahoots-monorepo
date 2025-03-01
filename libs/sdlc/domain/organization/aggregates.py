from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Set
from uuid import UUID

from .events import (
    OrganizationCreated, OrganizationNameUpdated,
    OrganizationMemberAdded, OrganizationMemberRemoved,
    OrganizationMemberRoleChanged, OrganizationArchived
)


@dataclass
class OrganizationMember:
    """Value object for organization member"""
    user_id: UUID
    role: str
    added_at: datetime
    added_by: UUID


@dataclass
class Organization:
    """Aggregate root for organizations"""
    organization_id: UUID
    name: str = ''
    description: str = ''
    status: str = 'active'  # active, archived
    created_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    members: Dict[UUID, OrganizationMember] = field(default_factory=dict)

    def apply_event(self, event):
        """Apply an event to update the aggregate state"""
        if isinstance(event, OrganizationCreated):
            self.name = event.name
            self.description = event.description
            self.created_at = event.timestamp
            self._add_member(
                user_id=event.created_by,
                role='admin',
                added_at=event.timestamp,
                added_by=event.created_by
            )

        elif isinstance(event, OrganizationNameUpdated):
            self.name = event.new_name

        elif isinstance(event, OrganizationMemberAdded):
            self._add_member(
                user_id=event.user_id,
                role=event.role,
                added_at=event.timestamp,
                added_by=event.added_by
            )

        elif isinstance(event, OrganizationMemberRemoved):
            if event.user_id in self.members:
                del self.members[event.user_id]

        elif isinstance(event, OrganizationMemberRoleChanged):
            if event.user_id in self.members:
                self.members[event.user_id].role = event.new_role

        elif isinstance(event, OrganizationArchived):
            self.status = 'archived'
            self.archived_at = event.archived_at

    def _add_member(self, user_id: UUID, role: str, added_at: datetime, added_by: UUID):
        """Helper method to add a member"""
        self.members[user_id] = OrganizationMember(
            user_id=user_id,
            role=role,
            added_at=added_at,
            added_by=added_by
        )

    def can_modify(self, user_id: UUID) -> bool:
        """Check if a user can modify the organization"""
        return (
            user_id in self.members and
            self.members[user_id].role == 'admin' and
            self.status == 'active'
        )

    def can_add_member(self, user_id: UUID, target_role: str) -> bool:
        """Check if a user can add a member with the given role"""
        if not self.can_modify(user_id):
            return False
        if target_role == 'admin':
            return self.members[user_id].role == 'admin'
        return True

    def can_remove_member(self, user_id: UUID, target_user_id: UUID) -> bool:
        """Check if a user can remove another member"""
        if not self.can_modify(user_id):
            return False
        if target_user_id not in self.members:
            return False
        # Prevent removing the last admin
        if self.members[target_user_id].role == 'admin':
            admin_count = sum(1 for m in self.members.values() if m.role == 'admin')
            if admin_count <= 1:
                return False
        return True

    def can_change_member_role(self, user_id: UUID, target_user_id: UUID, new_role: str) -> bool:
        """Check if a user can change another member's role"""
        if not self.can_modify(user_id):
            return False
        if target_user_id not in self.members:
            return False
        # Only admins can create other admins
        if new_role == 'admin':
            return self.members[user_id].role == 'admin'
        return True 