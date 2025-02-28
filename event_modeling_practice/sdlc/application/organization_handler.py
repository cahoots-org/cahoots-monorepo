from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ..domain.organization.aggregates import Organization
from ..domain.organization.commands import (
    CreateOrganization, UpdateOrganizationName,
    AddOrganizationMember, RemoveOrganizationMember,
    ChangeOrganizationMemberRole, ArchiveOrganization
)
from ..domain.organization.events import (
    OrganizationCreated, OrganizationNameUpdated,
    OrganizationMemberAdded, OrganizationMemberRemoved,
    OrganizationMemberRoleChanged, OrganizationArchived
)
from ..domain.organization.repository import OrganizationRepository
from ..domain.team.commands import (
    CreateTeam, AddTeamMember, UpdateTeamMemberRole,
    RemoveTeamMember, TransferTeamLeadership, ArchiveTeam
)
from ..domain.team.events import (
    TeamCreated, TeamMemberAdded, TeamMemberRoleChanged,
    TeamMemberRemoved, TeamLeadershipTransferred, TeamArchived
)
from ..domain.team.views import TeamView
from ..domain.events import Event, EventMetadata


class OrganizationHandler:
    """Handler for organization-related commands"""

    def __init__(self, event_store, view_store, organization_repository: OrganizationRepository):
        self.event_store = event_store
        self.view_store = view_store
        self.organization_repository = organization_repository

    def handle_create_organization(self, cmd: CreateOrganization) -> List[OrganizationCreated]:
        """Handle CreateOrganization command"""
        # Check if organization name is already taken
        existing_org = self.organization_repository.get_by_name(cmd.name)
        if existing_org:
            raise ValueError(f"Organization with name '{cmd.name}' already exists")

        organization_id = uuid4()
        organization = Organization(organization_id=organization_id)

        event = OrganizationCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=organization_id,
            name=cmd.name,
            description=cmd.description,
            created_by=cmd.created_by
        ).triggered_by(cmd.created_by).with_context(
            command_id=cmd.command_id,
            organization_name=cmd.name
        )
        
        organization.apply_event(event)
        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_update_name(self, cmd: UpdateOrganizationName) -> List[OrganizationNameUpdated]:
        """Handle UpdateOrganizationName command"""
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_modify(cmd.updated_by):
            raise ValueError("Insufficient permissions")

        # Check if new name is already taken
        existing_org = self.organization_repository.get_by_name(cmd.new_name)
        if existing_org and existing_org.organization_id != cmd.organization_id:
            raise ValueError(f"Organization with name '{cmd.new_name}' already exists")

        event = OrganizationNameUpdated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            old_name=organization.name,
            new_name=cmd.new_name,
            reason=cmd.reason,
            updated_by=cmd.updated_by
        ).triggered_by(cmd.updated_by).with_context(
            command_id=cmd.command_id,
            reason=cmd.reason
        )
        
        organization.apply_event(event)
        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_add_member(self, cmd: AddOrganizationMember) -> List[OrganizationMemberAdded]:
        """Handle AddOrganizationMember command"""
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_add_member(cmd.added_by, cmd.role):
            raise ValueError("Insufficient permissions")

        if cmd.user_id in organization.members:
            raise ValueError("User is already a member")

        event = OrganizationMemberAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            user_id=cmd.user_id,
            role=cmd.role,
            added_by=cmd.added_by
        ).triggered_by(cmd.added_by).with_context(
            command_id=cmd.command_id,
            member_role=cmd.role
        )
        
        organization.apply_event(event)
        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_remove_member(self, cmd: RemoveOrganizationMember) -> List[OrganizationMemberRemoved]:
        """Handle RemoveOrganizationMember command"""
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_remove_member(cmd.removed_by, cmd.user_id):
            raise ValueError("Cannot remove the last admin")

        event = OrganizationMemberRemoved(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            user_id=cmd.user_id,
            removed_by=cmd.removed_by,
            reason=cmd.reason
        ).triggered_by(cmd.removed_by).with_context(
            command_id=cmd.command_id,
            reason=cmd.reason
        )
        organization.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_change_member_role(self, cmd: ChangeOrganizationMemberRole) -> List[OrganizationMemberRoleChanged]:
        """Handle ChangeOrganizationMemberRole command"""
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_change_member_role(cmd.changed_by, cmd.user_id, cmd.new_role):
            raise ValueError("Insufficient permissions")

        if cmd.user_id not in organization.members:
            raise ValueError("User is not a member")

        event = OrganizationMemberRoleChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            user_id=cmd.user_id,
            old_role=organization.members[cmd.user_id].role,
            new_role=cmd.new_role,
            reason=cmd.reason,
            changed_by=cmd.changed_by
        ).triggered_by(cmd.changed_by).with_context(
            command_id=cmd.command_id,
            reason=cmd.reason
        )
        organization.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_archive_organization(self, cmd: ArchiveOrganization) -> List[OrganizationArchived]:
        """Handle ArchiveOrganization command"""
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_modify(cmd.archived_by):
            raise ValueError("Insufficient permissions")

        event = OrganizationArchived(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            reason=cmd.reason,
            archived_by=cmd.archived_by,
            archived_at=datetime.utcnow()
        ).triggered_by(cmd.archived_by).with_context(
            command_id=cmd.command_id,
            reason=cmd.reason
        )
        organization.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_create_team(self, cmd: CreateTeam) -> List[Event]:
        """Handle CreateTeam command"""
        # Check if organization exists and user has permission
        organization = self.organization_repository.get_by_id(cmd.organization_id)
        if not organization:
            raise ValueError(f"No organization found with id {cmd.organization_id}")

        if not organization.can_modify(cmd.created_by):
            raise ValueError("Insufficient permissions")

        team_id = uuid4()

        # Create the team
        team_created_event = TeamCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            organization_id=cmd.organization_id,
            team_id=team_id,
            name=cmd.name,
            description=cmd.description,
            created_by=cmd.created_by
        ).triggered_by(cmd.created_by).with_context(
            command_id=cmd.command_id,
            team_name=cmd.name
        )

        # Create the team view using the view store interface
        team_view = self.view_store.create_view(
            TeamView,
            team_id,
            organization_id=cmd.organization_id
        )

        # Apply and store the event
        team_view.apply_event(team_created_event)
        self.event_store.append(team_created_event)
        self.view_store.apply_event(team_created_event)

        return [team_created_event]

    def handle_add_team_member(self, cmd: AddTeamMember) -> List[Event]:
        """Handle AddTeamMember command"""
        # Get the team view to check permissions
        team_view = self.view_store.get_view(cmd.team_id, TeamView)
        if not team_view:
            raise ValueError(f"No team found with id {cmd.team_id}")

        # Check if the user adding the member is a lead or the team creator
        if cmd.added_by not in team_view.members:
            raise ValueError("Insufficient permissions")
        
        member_role = team_view.members[cmd.added_by]['role']
        if member_role != 'lead':
            raise ValueError("Insufficient permissions")

        events = []

        # If adding a new lead, first demote the current lead to member
        if cmd.role == 'lead':
            # Find the current lead
            old_lead_id = None
            for member_id, member in team_view.members.items():
                if member['role'] == 'lead':
                    old_lead_id = member_id
                    break

            if old_lead_id:
                # Create a leadership transfer event
                transfer_event = TeamLeadershipTransferred(
                    event_id=uuid4(),
                    timestamp=datetime.utcnow(),
                    metadata=EventMetadata(correlation_id=cmd.correlation_id),
                    team_id=cmd.team_id,
                    old_lead_id=old_lead_id,
                    new_lead_id=cmd.member_id,
                    transferred_by=cmd.added_by
                )
                events.append(transfer_event)
                self.event_store.append(transfer_event)
                self.view_store.apply_event(transfer_event)

        # Add the new member
        add_event = TeamMemberAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            team_id=cmd.team_id,
            member_id=cmd.member_id,
            role=cmd.role,
            added_by=cmd.added_by
        )
        events.append(add_event)
        self.event_store.append(add_event)
        self.view_store.apply_event(add_event)

        return events

    def handle_update_team_member_role(self, cmd: UpdateTeamMemberRole) -> List[TeamMemberRoleChanged]:
        """Handle UpdateTeamMemberRole command"""
        event = TeamMemberRoleChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            team_id=cmd.team_id,
            member_id=cmd.member_id,
            new_role=cmd.new_role,
            reason=cmd.reason,
            updated_by=cmd.updated_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_remove_team_member(self, cmd: RemoveTeamMember) -> List[TeamMemberRemoved]:
        """Handle RemoveTeamMember command"""
        event = TeamMemberRemoved(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            team_id=cmd.team_id,
            member_id=cmd.member_id,
            removed_by=cmd.removed_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_transfer_team_leadership(self, cmd: TransferTeamLeadership) -> List[TeamLeadershipTransferred]:
        """Handle TransferTeamLeadership command"""
        # Get the team view to find the current lead
        team_view = self.view_store.get_view(cmd.team_id, TeamView)
        if not team_view:
            raise ValueError(f"No team found with id {cmd.team_id}")

        # Find the current lead
        old_lead_id = None
        for member_id, member in team_view.members.items():
            if member['role'] == 'lead':
                old_lead_id = member_id
                break

        if not old_lead_id:
            raise ValueError("No current lead found")

        event = TeamLeadershipTransferred(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            team_id=cmd.team_id,
            old_lead_id=old_lead_id,
            new_lead_id=cmd.new_lead_id,
            transferred_by=cmd.transferred_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_archive_team(self, cmd: ArchiveTeam) -> List[TeamArchived]:
        """Handle ArchiveTeam command"""
        event = TeamArchived(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            team_id=cmd.team_id,
            reason=cmd.reason,
            archived_by=cmd.archived_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event] 