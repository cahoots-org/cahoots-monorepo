"""
Organization handler for tests
"""
from uuid import uuid4
from datetime import datetime
from ..test_imports import EventMetadata

# Import view classes
from ..views.organization_views import OrganizationDetailsView, OrganizationMembersView, OrganizationAuditLogView
from ..views.team_views import TeamView, TeamMembersView

# Organization events
class OrganizationCreated:
    """Event when an organization is created"""
    def __init__(self, event_id, timestamp, metadata, organization_id, name, description, created_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.organization_id = organization_id
        self.name = name
        self.description = description
        self.created_by = created_by

    @property
    def aggregate_id(self):
        return self.organization_id

class OrganizationMemberAdded:
    """Event when a member is added to an organization"""
    def __init__(self, event_id, timestamp, metadata, organization_id, user_id, role, added_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role
        self.added_by = added_by

    @property
    def aggregate_id(self):
        return self.organization_id

class OrganizationMemberRemoved:
    """Event when a member is removed from an organization"""
    def __init__(self, event_id, timestamp, metadata, organization_id, user_id, removed_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.organization_id = organization_id
        self.user_id = user_id
        self.removed_by = removed_by

    @property
    def aggregate_id(self):
        return self.organization_id

class OrganizationMemberRoleChanged:
    """Event when a member's role is changed"""
    def __init__(self, event_id, timestamp, metadata, organization_id, user_id, old_role, new_role, changed_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.organization_id = organization_id
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role
        self.changed_by = changed_by

    @property
    def aggregate_id(self):
        return self.organization_id

class OrganizationNameUpdated:
    """Event when an organization's name is updated"""
    def __init__(self, event_id, timestamp, metadata, organization_id, new_name, reason, updated_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.organization_id = organization_id
        self.new_name = new_name
        self.reason = reason
        self.updated_by = updated_by

    @property
    def aggregate_id(self):
        return self.organization_id

# Team events
class TeamCreated:
    """Event when a team is created"""
    def __init__(self, event_id, timestamp, metadata, team_id, organization_id, name, description, created_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.organization_id = organization_id
        self.name = name
        self.description = description
        self.created_by = created_by

    @property
    def aggregate_id(self):
        return self.team_id

class TeamMemberAdded:
    """Event when a member is added to a team"""
    def __init__(self, event_id, timestamp, metadata, team_id, user_id, role, added_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.user_id = user_id
        self.role = role
        self.added_by = added_by

    @property
    def aggregate_id(self):
        return self.team_id

class TeamMemberRoleChanged:
    """Event when a team member's role is changed"""
    def __init__(self, event_id, timestamp, metadata, team_id, user_id, old_role, new_role, updated_by, reason):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role
        self.updated_by = updated_by
        self.reason = reason

    @property
    def aggregate_id(self):
        return self.team_id

class TeamMemberRemoved:
    """Event when a member is removed from a team"""
    def __init__(self, event_id, timestamp, metadata, team_id, user_id, removed_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.user_id = user_id
        self.removed_by = removed_by

    @property
    def aggregate_id(self):
        return self.team_id

class TeamArchived:
    """Event when a team is archived"""
    def __init__(self, event_id, timestamp, metadata, team_id, reason, archived_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.reason = reason
        self.archived_by = archived_by

    @property
    def aggregate_id(self):
        return self.team_id

class TeamLeadershipTransferred:
    """Event when team leadership is transferred"""
    def __init__(self, event_id, timestamp, metadata, team_id, new_lead_id, transferred_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.team_id = team_id
        self.new_lead_id = new_lead_id
        self.transferred_by = transferred_by

    @property
    def aggregate_id(self):
        return self.team_id

class OrganizationHandler:
    """Handler for organization commands in tests"""
    
    def __init__(self, event_store, view_store, organization_repository=None):
        """Initialize the organization handler"""
        self.event_store = event_store
        self._view_store = view_store
        self._organization_repository = organization_repository
        
        # Register view factories
        from ..views.organization_views import OrganizationDetailsView, OrganizationMembersView, OrganizationAuditLogView
        from ..views.team_views import TeamView, TeamMembersView
        
        # Store references to the view classes for easy access
        self.org_details_view_factory = OrganizationDetailsView
        self.org_members_view_factory = OrganizationMembersView
        self.org_audit_log_factory = OrganizationAuditLogView
        self.team_view_factory = TeamView
        self.team_members_view_factory = TeamMembersView
    
    def handle_create_organization(self, cmd):
        """Handle create organization command"""
        # Create a proper event object instead of a dictionary
        organization_id = uuid4()
        event = OrganizationCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            organization_id=organization_id,
            name=cmd.name,
            description=cmd.description,
            created_by=cmd.created_by
        )
        # Store the event
        self.event_store.append(event)
        return [event]
    
    def handle_add_member(self, cmd):
        """Handle add member command"""
        # Add validation
        members_view = self._view_store.get_view(cmd.organization_id, OrganizationMembersView)
        
        # Check if the user is already a member
        if cmd.user_id in members_view.members:
            raise ValueError("User is already a member")
        
        # Check if the user adding has admin permissions
        if cmd.added_by not in members_view.roles['admin']:
            raise ValueError("Insufficient permissions")
        
        # Create a proper event object
        event = OrganizationMemberAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            organization_id=cmd.organization_id,
            user_id=cmd.user_id,
            role=cmd.role,
            added_by=cmd.added_by
        )
        
        # Store the event
        self.event_store.append(event)
        
        # Update members view
        members_view.members[cmd.user_id] = {
            'id': cmd.user_id,
            'role': cmd.role,
            'added_at': event.timestamp,
            'added_by': cmd.added_by
        }
        
        # Initialize the role list if it doesn't exist
        if cmd.role not in members_view.roles:
            members_view.roles[cmd.role] = []
            
        # Only add to the role list if not already there
        if cmd.user_id not in members_view.roles[cmd.role]:
            members_view.roles[cmd.role].append(cmd.user_id)
        
        # Manually update the details view
        details_view = self._view_store.get_view(cmd.organization_id, OrganizationDetailsView)
        
        # Set member count directly based on the members dict
        details_view.member_count = len(members_view.members)
        
        # Count admin users
        admin_count = len(members_view.roles.get('admin', []))
        details_view.admin_count = admin_count
        
        # Save views
        self._view_store.save_view(cmd.organization_id, details_view)
        self._view_store.save_view(cmd.organization_id, members_view)
        
        print(f"After adding member: {cmd.user_id}")
        print(f"Members: {list(members_view.members.keys())}")
        print(f"Member count set to: {details_view.member_count}")
        
        return [event]
    
    def handle_remove_member(self, cmd):
        """Handle remove member command"""
        # Add validation
        members_view = self._view_store.get_view(cmd.organization_id, OrganizationMembersView)
        details_view = self._view_store.get_view(cmd.organization_id, OrganizationDetailsView)
        
        # Check if the user exists
        if cmd.user_id not in members_view.members:
            print(f"User {cmd.user_id} not in members list: {list(members_view.members.keys())}")
            raise ValueError("User is not a member")
        
        # Get user's role
        user_role = members_view.members[cmd.user_id]['role']
        
        # Check if user is admin and is the last admin
        if user_role == 'admin' and details_view.admin_count <= 1:
            raise ValueError("Cannot remove the last admin")
        
        # Create a proper event object
        event = OrganizationMemberRemoved(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            organization_id=cmd.organization_id,
            user_id=cmd.user_id,
            removed_by=cmd.removed_by
        )
        
        # Store the event
        self.event_store.append(event)
        
        # Update members view - check if role exists in the roles dict
        if user_role in members_view.roles and cmd.user_id in members_view.roles[user_role]:
            members_view.roles[user_role].remove(cmd.user_id)
            
        # Remove from members dictionary if exists
        if cmd.user_id in members_view.members:
            del members_view.members[cmd.user_id]
        
        # Manually update the details view
        # Set member count directly based on the members dict
        details_view.member_count = len(members_view.members)
        
        # Count admin users
        admin_count = len(members_view.roles.get('admin', []))
        details_view.admin_count = admin_count
        
        # Save views
        self._view_store.save_view(cmd.organization_id, details_view)
        self._view_store.save_view(cmd.organization_id, members_view)
        
        print(f"After removing member: {cmd.user_id}")
        print(f"Members: {list(members_view.members.keys())}")
        print(f"Member count set to: {details_view.member_count}")
        
        return [event]
    
    def handle_update_name(self, cmd):
        """Handle update name command"""
        # Add validation - check if user is admin
        members_view = self._view_store.get_view(cmd.organization_id, OrganizationMembersView)
        
        # Check if user is admin
        if cmd.updated_by not in members_view.roles['admin']:
            raise ValueError("Insufficient permissions")
        
        # Create the event
        event = OrganizationNameUpdated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            organization_id=cmd.organization_id,
            new_name=cmd.new_name,
            reason=cmd.reason,
            updated_by=cmd.updated_by
        )
        
        # Store the event
        self.event_store.append(event)
        
        # Manually update the view
        details_view = self._view_store.get_view(cmd.organization_id, OrganizationDetailsView)
        details_view.name = cmd.new_name
        self._view_store.save_view(cmd.organization_id, details_view)
        
        return [event]

    def handle_create_team(self, cmd):
        """Handle create team command"""
        # Generate a new UUID for the team
        team_id = uuid4()
        
        # Create the team created event
        event = TeamCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.created_by
            ),
            team_id=team_id,
            organization_id=cmd.organization_id,
            name=cmd.name,
            description=cmd.description,
            created_by=cmd.created_by
        )
        
        # Store the event in the event store
        self.event_store.append_events(team_id, [event])
        
        # Create a new team view and initialize it
        team_view = self._view_store.get_view(
            team_id,
            self.team_view_factory
        )
        members_view = self._view_store.get_view(
            team_id,
            self.team_members_view_factory
        )
        
        # Initialize the members with the creator as a lead
        team_view.apply_event(event)
        members_view.apply_event(event)
        
        # Store the views
        self._view_store.save_view(team_id, team_view)
        self._view_store.save_view(team_id, members_view)
        
        print(f"Team {team_id} created in organization {cmd.organization_id}")
        print(f"Team name: {cmd.name}")
        print(f"Created by: {cmd.created_by}")
        
        return [event]
        
    def handle_add_team_member(self, cmd):
        """Handle add team member command"""
        # Get the team view
        team_view = self._view_store.get_view(cmd.team_id, self.team_view_factory)
        members_view = self._view_store.get_view(cmd.team_id, self.team_members_view_factory)
        
        # Check if the team exists
        if not team_view:
            raise ValueError(f"Team {cmd.team_id} not found")
        
        # Check if the user is already a member
        if cmd.member_id in members_view.members:
            raise ValueError(f"User {cmd.member_id} is already a member of the team")
        
        # Check if the user adding has permissions (must be a lead or admin)
        if cmd.created_by not in members_view.members:
            org_members_view = self._view_store.get_view(team_view.organization_id, self.org_members_view_factory)
            if not org_members_view or cmd.created_by not in org_members_view.roles['admin']:
                raise ValueError("Insufficient permissions")
        else:
            member_role = members_view.members[cmd.created_by]["role"]
            if member_role != "lead":
                raise ValueError("Insufficient permissions")
        
        # Create the event
        event = TeamMemberAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.created_by
            ),
            team_id=cmd.team_id,
            user_id=cmd.member_id,
            role=cmd.role,
            added_by=cmd.created_by
        )
        
        # Store the event
        self.event_store.append_events(cmd.team_id, [event])
        
        # Update the members view
        members_view.apply_event(event)
        
        # Save the updated views
        self._view_store.save_view(cmd.team_id, members_view)
        
        print(f"User {cmd.member_id} added to team {cmd.team_id} with role {cmd.role}")
        
        return [event]
        
    def handle_update_team_member_role(self, cmd):
        """Handle update team member role command"""
        # Get the team views
        members_view = self._view_store.get_view(cmd.team_id, self.team_members_view_factory)
        
        # Check if the team exists
        if not members_view:
            raise ValueError(f"Team {cmd.team_id} not found")
        
        # Check if the user is a member
        if cmd.user_id not in members_view.members:
            raise ValueError(f"User {cmd.user_id} is not a member of the team")
        
        # Check if the current user has lead permissions
        if cmd.created_by not in members_view.members:
            org_id = self._view_store.get_view(cmd.team_id, self.team_view_factory).organization_id
            org_members_view = self._view_store.get_view(org_id, self.org_members_view_factory)
            if not org_members_view or cmd.created_by not in org_members_view.admins:
                raise ValueError("Insufficient permissions to update member roles")
        else:
            member_role = members_view.members[cmd.created_by]["role"]
            if member_role != "lead":
                raise ValueError("Only team leads can update member roles")
        
        # Create the event
        event = TeamMemberRoleChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.created_by
            ),
            team_id=cmd.team_id,
            user_id=cmd.user_id,
            old_role=members_view.members[cmd.user_id]["role"],
            new_role=cmd.new_role,
            updated_by=cmd.created_by,
            reason=cmd.reason
        )
        
        # Store the event
        self.event_store.append_events(cmd.team_id, [event])
        
        # Update the view
        members_view.apply_event(event)
        
        # Save the updated view
        self._view_store.save_view(cmd.team_id, members_view)
        
        print(f"User {cmd.user_id} role updated from {members_view.members[cmd.user_id]['role']} to {cmd.new_role}")
        
        return [event]
        
    def handle_remove_team_member(self, cmd):
        """Handle remove team member command"""
        # Get the team views
        members_view = self._view_store.get_view(cmd.team_id, self.team_members_view_factory)
        
        # Check if the team exists
        if not members_view:
            raise ValueError(f"Team {cmd.team_id} not found")
        
        # Check if the user is a member
        if cmd.user_id not in members_view.members:
            raise ValueError(f"User {cmd.user_id} is not a member of the team")
        
        # Check permissions (must be a lead or an admin of the organization)
        if cmd.created_by not in members_view.members:
            org_id = self._view_store.get_view(cmd.team_id, self.team_view_factory).organization_id
            org_members_view = self._view_store.get_view(org_id, self.org_members_view_factory)
            if not org_members_view or cmd.created_by not in org_members_view.admins:
                raise ValueError("Insufficient permissions to remove team members")
        else:
            member_role = members_view.members[cmd.created_by]["role"]
            if member_role != "lead":
                raise ValueError("Only team leads can remove members")
        
        # Prevent removing the last lead
        if members_view.members[cmd.user_id]["role"] == "lead":
            lead_count = sum(1 for member in members_view.members.values() if member["role"] == "lead")
            if lead_count <= 1:
                raise ValueError("Cannot remove the last team lead")
        
        # Create the event
        event = TeamMemberRemoved(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.created_by
            ),
            team_id=cmd.team_id,
            user_id=cmd.user_id,
            removed_by=cmd.created_by
        )
        
        # Store the event
        self.event_store.append_events(cmd.team_id, [event])
        
        # Update the view
        members_view.apply_event(event)
        
        # Save the updated view
        self._view_store.save_view(cmd.team_id, members_view)
        
        print(f"User {cmd.user_id} removed from team {cmd.team_id}")
        
        return [event]
        
    def handle_archive_team(self, cmd):
        """Handle archive team command"""
        # Get the team view
        team_view = self._view_store.get_view(cmd.team_id, self.team_view_factory)
        members_view = self._view_store.get_view(cmd.team_id, self.team_members_view_factory)
        
        # Check if the team exists
        if not team_view:
            raise ValueError(f"Team {cmd.team_id} not found")
        
        # Check permissions (must be an organization admin)
        org_members_view = self._view_store.get_view(team_view.organization_id, self.org_members_view_factory)
        if not org_members_view or cmd.archived_by not in org_members_view.roles['admin']:
            raise ValueError("Only organization admins can archive teams")
        
        # Create the event
        event = TeamArchived(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.archived_by
            ),
            team_id=cmd.team_id,
            reason=cmd.reason,
            archived_by=cmd.archived_by
        )
        
        # Store the event
        self.event_store.append_events(cmd.team_id, [event])
        
        # Update the view
        team_view.apply_event(event)
        
        # Save the updated view
        self._view_store.save_view(cmd.team_id, team_view)
        
        # Notify team members (in a real system, this would trigger notifications)
        for user_id in members_view.members:
            print(f"Notification to user {user_id}: Team {team_view.name} has been archived")
        
        print(f"Team {cmd.team_id} archived by {cmd.archived_by}")
        
        return [event]
        
    def handle_transfer_team_leadership(self, cmd):
        """Handle transfer team leadership command"""
        # Get the team view
        members_view = self._view_store.get_view(cmd.team_id, self.team_members_view_factory)
        
        # Check if the team exists
        if not members_view:
            raise ValueError(f"Team {cmd.team_id} not found")
        
        # Check if both users are members
        if cmd.created_by not in members_view.members:
            raise ValueError(f"User {cmd.created_by} is not a member of the team")
        
        if cmd.new_lead_id not in members_view.members:
            raise ValueError(f"User {cmd.new_lead_id} is not a member of the team")
        
        # Check if the current user is a lead
        if members_view.members[cmd.created_by]["role"] != "lead":
            raise ValueError("Only team leads can transfer leadership")
        
        # Create the event
        event = TeamLeadershipTransferred(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1,
                correlation_id=cmd.correlation_id,
                actor_id=cmd.created_by
            ),
            team_id=cmd.team_id,
            new_lead_id=cmd.new_lead_id,
            transferred_by=cmd.created_by
        )
        
        # Store the event
        self.event_store.append_events(cmd.team_id, [event])
        
        # Update the view
        members_view.apply_event(event)
        
        # Save the updated view
        self._view_store.save_view(cmd.team_id, members_view)
        
        print(f"Leadership transferred from {cmd.created_by} to {cmd.new_lead_id}")
        
        return [event] 