"""
Team views for tests
"""

from uuid import UUID


class TeamView:
    """View that represents a team's state"""

    def __init__(self, team_id: UUID):
        self.team_id = team_id
        self.name = ""
        self.description = ""
        self.organization_id = None
        self.created_by = None
        self.members = {}  # Dict of user_id -> role
        self.status = "active"
        self.created_at = None
        self.archived_at = None
        self.archived_reason = None
        self.last_notification = None

    def apply_event(self, event):
        """Apply an event to update the view state"""
        event_type = event.__class__.__name__

        if event_type == "TeamCreated":
            self.name = event.name
            self.description = event.description
            self.organization_id = event.organization_id
            self.created_by = event.created_by
            self.created_at = (
                event.metadata.created_at if hasattr(event, "metadata") else event.timestamp
            )
            # Add the creator as a lead automatically
            self.members[event.created_by] = {"role": "lead"}

        elif event_type == "TeamMemberAdded":
            # Add member to the team with their role
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            self.members[user_id] = {"role": event.role}

        elif event_type == "TeamMemberRoleUpdated" or event_type == "TeamMemberRoleChanged":
            # Update member's role
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            if user_id in self.members:
                self.members[user_id]["role"] = event.new_role

        elif event_type == "TeamMemberRemoved":
            # Remove member from the team
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            if user_id in self.members:
                del self.members[user_id]

        elif event_type == "TeamArchived":
            # Archive the team
            self.status = "archived"
            self.archived_at = (
                event.metadata.created_at if hasattr(event, "metadata") else event.timestamp
            )
            self.archived_reason = event.reason
            # Set the notification for team members
            self.last_notification = {
                "type": "team_archived",
                "message": f"Team {self.name} has been archived",
                "timestamp": event.timestamp,
            }

        elif event_type == "TeamLeadershipTransferred":
            # Transfer leadership: update roles
            old_lead = event.old_lead_id if hasattr(event, "old_lead_id") else event.transferred_by

            if event.new_lead_id in self.members:
                # Former lead becomes a regular member
                if old_lead in self.members and self.members[old_lead]["role"] == "lead":
                    self.members[old_lead]["role"] = "member"
                # New lead gets the lead role
                self.members[event.new_lead_id]["role"] = "lead"


class TeamMembersView:
    """View that tracks team members and their roles"""

    def __init__(self, team_id: UUID):
        self.team_id = team_id
        self.members = {}  # Dict of user_id -> {'role': role}

    def apply_event(self, event):
        """Apply an event to update the view state"""
        event_type = event.__class__.__name__

        if event_type == "TeamCreated":
            # Add the creator as the first member with lead role
            self.members[event.created_by] = {"role": "lead"}

        elif event_type == "TeamMemberAdded":
            # Add new member with their role
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            self.members[user_id] = {"role": event.role}

        elif event_type == "TeamMemberRoleUpdated" or event_type == "TeamMemberRoleChanged":
            # Update member's role
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            if user_id in self.members:
                self.members[user_id]["role"] = event.new_role

        elif event_type == "TeamMemberRemoved":
            # Remove member from the team
            user_id = event.user_id if hasattr(event, "user_id") else event.member_id
            if user_id in self.members:
                del self.members[user_id]

        elif event_type == "TeamLeadershipTransferred":
            # Transfer leadership within the team
            old_lead = event.old_lead_id if hasattr(event, "old_lead_id") else event.transferred_by

            if old_lead in self.members and self.members[old_lead]["role"] == "lead":
                self.members[old_lead]["role"] = "member"

            if event.new_lead_id in self.members:
                self.members[event.new_lead_id]["role"] = "lead"
