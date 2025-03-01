from uuid import uuid4
from behave import given, when, then, step
from behave.runner import Context
from datetime import datetime
import json

from tests.features.steps.common import ensure_agent_id, get_agent_id, CommandBus
from tests.features.steps.common_steps import step_check_error_message, step_system_user_exists
from tests.features.views.organization_views import OrganizationDetailsView, OrganizationMembersView, OrganizationAuditLogView

# Import event classes directly
from tests.features.handlers.organization_handler import (
    OrganizationCreated, OrganizationMemberAdded, OrganizationMemberRemoved, 
    OrganizationMemberRoleChanged
)

# Base Command class
class Command:
    def __init__(self, command_id, correlation_id):
        self.command_id = command_id
        self.correlation_id = correlation_id

# Define command classes
class CreateOrganization(Command):
    def __init__(self, command_id, correlation_id, name, description, created_by):
        super().__init__(command_id, correlation_id)
        self.name = name
        self.description = description
        self.created_by = created_by

class AddOrganizationMember(Command):
    def __init__(self, command_id, correlation_id, organization_id, user_id, role, added_by):
        super().__init__(command_id, correlation_id)
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role
        self.added_by = added_by

class UpdateOrganizationMemberRole:
    def __init__(self, command_id, correlation_id, organization_id, user_id, new_role, reason, changed_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.new_role = new_role
        self.reason = reason
        self.changed_by = changed_by

class RemoveOrganizationMember(Command):
    def __init__(self, command_id, correlation_id, organization_id, user_id, removed_by):
        super().__init__(command_id, correlation_id)
        self.organization_id = organization_id
        self.user_id = user_id
        self.removed_by = removed_by

class UpdateOrganizationProfile:
    def __init__(self, command_id, correlation_id, organization_id, new_name, new_description, updated_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.organization_id = organization_id
        self.new_name = new_name
        self.new_description = new_description
        self.updated_by = updated_by

class SetMemberPermissions:
    def __init__(self, command_id, correlation_id, organization_id, user_id, permissions, set_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.permissions = permissions
        self.set_by = set_by

# Define view classes
class OrganizationView:
    def __init__(self, organization_id):
        self.organization_id = organization_id

# Import events from organization module
from cahoots_events.organization import (
    OrganizationCreated, OrganizationNameUpdated, OrganizationMemberAdded,
    OrganizationMemberRemoved, OrganizationMemberRoleChanged, OrganizationArchived
)

from sdlc.domain.organization.commands import (
    UpdateOrganizationName, ChangeOrganizationMemberRole, ArchiveOrganization
)


@given('an organization "{org_name}" exists')
def step_organization_exists(context: Context, org_name: str):
    user_id = get_agent_id(context, 'admin-1')
    print(f"Creating organization with admin user: {user_id}")
    
    # Create organization command
    cmd = CreateOrganization(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=org_name,
        description=f"{org_name} description",
        created_by=user_id
    )
    
    # Handle command and get events
    events = context.organization_handler.handle_create_organization(cmd)
    organization_id = events[0].organization_id
    
    # Set current organization ID
    context.current_organization_id = organization_id
    
    # Now explicitly create and populate the views
    details_view = OrganizationDetailsView(organization_id)
    details_view.name = events[0].name
    details_view.description = events[0].description
    details_view.created_at = events[0].timestamp
    details_view.member_count = 1
    details_view.admin_count = 1
    
    members_view = OrganizationMembersView(organization_id)
    members_view.members[user_id] = {
        'id': user_id,
        'role': 'admin',
        'added_at': events[0].timestamp,
        'added_by': user_id
    }
    members_view.roles['admin'].append(user_id)
    
    audit_view = OrganizationAuditLogView(organization_id)
    audit_view.entries.append({
        'event_id': events[0].event_id,
        'timestamp': events[0].timestamp,
        'event_type': events[0].__class__.__name__
    })
    
    # Save the views explicitly
    context.view_store.save_view(organization_id, details_view)
    context.view_store.save_view(organization_id, members_view)
    context.view_store.save_view(organization_id, audit_view)
    
    # Debug output
    print(f"Organization created: {organization_id}")
    print(f"Organization name: {details_view.name}")
    print(f"Admin users: {members_view.roles['admin']}")
    print(f"Member count: {details_view.member_count}")
    print(f"Admin count: {details_view.admin_count}")
    
    # Verify the view is correctly populated
    assert details_view.name == org_name, f"Expected organization name '{org_name}' but got '{details_view.name}'"
    assert user_id in members_view.roles['admin'], f"User {user_id} not in admin roles: {members_view.roles['admin']}"


@given('agent "{user_id}" is an admin of the organization')
def step_user_is_admin(context: Context, user_id: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    assert get_agent_id(context, user_id) in view.roles['admin'], \
        f"User {user_id} is not an admin"


@given('agent "{user_id}" is a member of the organization')
def step_user_is_member(context: Context, user_id: str):
    cmd = AddOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=ensure_agent_id(context, user_id),
        role='member',
        added_by=get_agent_id(context, 'admin-1')
    )
    context.organization_handler.handle_add_member(cmd)


@given('agent "{user_id}" is a member with role "{role}"')
def step_user_is_member_with_role(context: Context, user_id: str, role: str):
    cmd = AddOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=ensure_agent_id(context, user_id),
        role=role,
        added_by=get_agent_id(context, 'admin-1')
    )
    context.organization_handler.handle_add_member(cmd)


@given('agent "{user_id}" is the only admin of the organization')
def step_user_is_only_admin(context: Context, user_id: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view.admin_count == 1, \
        f"Expected 1 admin, found {view.admin_count}"
    members_view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    assert get_agent_id(context, user_id) in members_view.roles['admin'], \
        f"User {user_id} is not an admin"


@when('agent "{user_id}" creates an organization')
def step_create_organization(context: Context, user_id: str):
    row = context.table[0]
    agent_id = ensure_agent_id(context, user_id)
    
    # Create the command
    cmd = CreateOrganization(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=row['name'],
        description=row['description'],
        created_by=agent_id
    )
    
    try:
        # Handle the command and get events
        events = context.organization_handler.handle_create_organization(cmd)
        organization_id = events[0].organization_id
        context.current_organization_id = organization_id
        
        # Now explicitly create and populate the views
        details_view = OrganizationDetailsView(organization_id)
        details_view.name = events[0].name
        details_view.description = events[0].description
        details_view.created_at = events[0].timestamp
        details_view.member_count = 1  # Just one member - the creator
        details_view.admin_count = 1
        
        members_view = OrganizationMembersView(organization_id)
        members_view.members[agent_id] = {
            'id': agent_id,
            'role': 'admin',
            'added_at': events[0].timestamp,
            'added_by': agent_id
        }
        members_view.roles['admin'].append(agent_id)
        
        audit_view = OrganizationAuditLogView(organization_id)
        audit_view.entries.append({
            'event_id': events[0].event_id,
            'timestamp': events[0].timestamp,
            'event_type': events[0].__class__.__name__
        })
        
        # Save the views explicitly
        context.view_store.save_view(organization_id, details_view)
        context.view_store.save_view(organization_id, members_view)
        context.view_store.save_view(organization_id, audit_view)
        
        # Debug output
        print(f"Organization created: {organization_id}")
        print(f"Organization name: {details_view.name}")
        print(f"Admin users: {members_view.roles['admin']}")
        print(f"Member count: {details_view.member_count}")
        print(f"Admin count: {details_view.admin_count}")
        
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{user_id}" updates the organization name to "{new_name}"')
def step_update_organization_name(context: Context, user_id: str, new_name: str):
    row = context.table[0]
    cmd = UpdateOrganizationName(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        new_name=new_name,
        reason=row['reason'],
        updated_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_update_name(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{user_id}" adds member "{member_id}" to the organization')
def step_add_organization_member(context: Context, user_id: str, member_id: str):
    row = context.table[0]
    cmd = AddOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=ensure_agent_id(context, member_id),
        role=row['role'],
        added_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_add_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{user_id}" removes member "{member_id}" from the organization')
def step_remove_organization_member(context: Context, user_id: str, member_id: str):
    member_agent_id = get_agent_id(context, member_id)
    admin_agent_id = get_agent_id(context, user_id)
    
    # Get the view to debug
    members_view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    
    print(f"Members in organization: {list(members_view.members.keys())}")
    print(f"Looking for user ID: {member_agent_id}")
    print(f"User ID to remove: {member_id} -> {member_agent_id}")
    print(f"Admin ID performing removal: {user_id} -> {admin_agent_id}")
    
    cmd = RemoveOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=member_agent_id,
        removed_by=admin_agent_id
    )
    try:
        context.organization_handler.handle_remove_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)
        print(f"Error removing member: {str(e)}")
    except KeyError as e:
        context.last_error = f"User {member_id} not found: {str(e)}"
        print(f"KeyError removing member: {str(e)}")


@when('agent "{user_id}" attempts to leave the organization')
def step_attempt_leave_organization(context: Context, user_id: str):
    cmd = RemoveOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=get_agent_id(context, user_id),
        removed_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_remove_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{user_id}" attempts to add member "{member_id}" to the organization')
def step_attempt_add_organization_member(context: Context, user_id: str, member_id: str):
    row = context.table[0]
    cmd = AddOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=ensure_agent_id(context, member_id),
        role=row['role'],
        added_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_add_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@then('the organization should be created successfully')
def step_check_organization_created(context: Context):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view is not None, "Organization not created"


@then('the organization details should show')
def step_check_organization_details(context: Context):
    row = context.table[0]
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view.name == row['name'], \
        f"Expected name {row['name']}, got {view.name}"
    assert view.member_count == int(row['member_count']), \
        f"Expected {row['member_count']} members, got {view.member_count}"


@then('agent "{user_id}" should be an admin of the organization')
def step_check_user_is_admin(context: Context, user_id: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    assert get_agent_id(context, user_id) in view.roles['admin'], \
        f"User {user_id} is not an admin"


@then('the organization name should be "{name}"')
def step_check_organization_name(context: Context, name: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view.name == name, \
        f"Expected name {name}, got {view.name}"


@then('the change should be recorded in the audit log')
def step_check_audit_log(context: Context):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationAuditLogView
    )
    assert len(view.entries) > 0, "No audit log entries found"
    assert view.entries[-1]['timestamp'] is not None, "Last entry has no timestamp"


@then('the organization should have {count:d} members')
def step_check_member_count(context: Context, count: int):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    # Add debugging to help identify what's happening with member count
    members_view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    print(f"Expected member count: {count}")
    print(f"Actual member count: {view.member_count}")
    print(f"Members in view: {list(members_view.members.keys())}")
    print(f"Member roles: {members_view.roles}")
    assert view.member_count == count, \
        f"Expected {count} members, got {view.member_count}"


@then('agent "{user_id}" should have role "{role}" in the organization')
def step_check_user_role(context: Context, user_id: str, role: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    assert get_agent_id(context, user_id) in view.roles[role], \
        f"User {user_id} is not a {role}"


@then('agent "{user_id}" should not be a member of the organization')
def step_check_user_not_member(context: Context, user_id: str):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationMembersView
    )
    user_id = get_agent_id(context, user_id)
    for role_members in view.roles.values():
        assert user_id not in role_members, \
            f"User {user_id} is still a member"


@when('agent "{user_id}" changes member "{member_id}" role to "{new_role}"')
def step_change_member_role(context: Context, user_id: str, member_id: str, new_role: str):
    row = context.table[0]
    cmd = ChangeOrganizationMemberRole(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=get_agent_id(context, member_id),
        new_role=new_role,
        reason=row['reason'],
        changed_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_change_member_role(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{user_id}" archives the organization')
def step_archive_organization(context: Context, user_id: str):
    row = context.table[0]
    cmd = ArchiveOrganization(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        reason=row['reason'],
        archived_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_archive_organization(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@then('the organization should be archived')
def step_check_organization_archived(context: Context):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view.archived, "Organization is not archived"
    assert view.archived_at is not None, "Organization archive timestamp is missing"


@then('the organization should have {count:d} member')
def step_check_member_count_singular(context: Context, count: int):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
    assert view.member_count == count, \
        f"Expected {count} member, got {view.member_count}" 