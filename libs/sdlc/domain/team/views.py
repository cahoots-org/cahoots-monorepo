from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import UUID

from ..events import Event
from .events import (
    TeamArchived,
    TeamCreated,
    TeamLeadershipTransferred,
    TeamMemberAdded,
    TeamMemberRemoved,
    TeamMemberRoleChanged,
)


@dataclass
class TeamView:
    """View of team details and members"""

    team_id: UUID
    organization_id: Optional[UUID] = None
    name: str = ""
    description: str = ""
    status: str = "active"
    members: Dict[UUID, Dict] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_notification: Optional[Dict] = None

    def apply_event(self, event: Event) -> None:
        """Update view based on events"""
        if isinstance(event, TeamCreated):
            self.organization_id = event.organization_id
            self.name = event.name
            self.description = event.description
            self.created_at = event.timestamp.isoformat()
            self.updated_at = event.timestamp.isoformat()
            # Add creator as lead
            self.members[event.created_by] = {
                "id": event.created_by,
                "role": "lead",
                "added_by": event.created_by,
                "added_at": event.timestamp.isoformat(),
            }

        elif isinstance(event, TeamMemberAdded):
            if event.member_id not in self.members:  # Only add if not already a member
                self.members[event.member_id] = {
                    "id": event.member_id,
                    "role": event.role,
                    "added_by": event.added_by,
                    "added_at": event.timestamp.isoformat(),
                }
                self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, TeamMemberRoleChanged):
            if event.member_id in self.members:
                self.members[event.member_id]["role"] = event.new_role
                self.members[event.member_id]["updated_at"] = event.timestamp.isoformat()
                self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, TeamMemberRemoved):
            if event.member_id in self.members:
                del self.members[event.member_id]
                self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, TeamLeadershipTransferred):
            # Update new lead
            if event.new_lead_id in self.members:
                self.members[event.new_lead_id]["role"] = "lead"
                self.members[event.new_lead_id]["updated_at"] = event.timestamp.isoformat()

            # Update old lead to member role
            if event.old_lead_id in self.members:
                self.members[event.old_lead_id]["role"] = "member"
                self.members[event.old_lead_id]["updated_at"] = event.timestamp.isoformat()

            self.updated_at = event.timestamp.isoformat()

        elif isinstance(event, TeamArchived):
            self.status = "archived"
            self.updated_at = event.timestamp.isoformat()
            self.last_notification = {
                "type": "team_archived",
                "reason": event.reason,
                "archived_by": event.archived_by,
                "timestamp": event.timestamp.isoformat(),
            }
