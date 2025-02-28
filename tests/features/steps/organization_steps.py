from uuid import uuid4
from datetime import datetime, timedelta
from behave import given, when, then
from behave.runner import Context
from features.steps.common import ensure_agent_id, get_agent_id
from features.steps.common_steps import step_check_error_message, step_system_user_exists

# Define command classes for organization operations
class CreateOrganization:
    def __init__(self, command_id, correlation_id, name, description, created_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.name = name
        self.description = description
        self.created_by = created_by

class AddOrganizationMember:
    def __init__(self, command_id, correlation_id, organization_id, user_id, role, added_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
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

class RemoveOrganizationMember:
    def __init__(self, command_id, correlation_id, organization_id, user_id, removed_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
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

class OrganizationMembersView:
    def __init__(self, organization_id):
        self.organization_id = organization_id
        self.roles = {'admin': [], 'member': []}

# Import events from organization module
from cahoots_events.organization import (
    OrganizationCreated, OrganizationNameUpdated, OrganizationMemberAdded,
    OrganizationMemberRemoved, OrganizationMemberRoleChanged, OrganizationArchived
)

from sdlc.domain.organization.commands import (
    UpdateOrganizationName, ChangeOrganizationMemberRole, ArchiveOrganization
)
from sdlc.domain.organization.views import (
    OrganizationDetailsView, OrganizationAuditLogView
)


@given('an organization "{org_name}" exists')
def step_organization_exists(context: Context, org_name: str):
    cmd = CreateOrganization(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=org_name,
        description=f"{org_name} description",
        created_by=get_agent_id(context, 'admin-1')
    )
    events = context.organization_handler.handle_create_organization(cmd)
    context.current_organization_id = events[0].organization_id


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
    cmd = CreateOrganization(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=row['name'],
        description=row['description'],
        created_by=ensure_agent_id(context, user_id)
    )
    try:
        events = context.organization_handler.handle_create_organization(cmd)
        context.current_organization_id = events[0].organization_id
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
    cmd = RemoveOrganizationMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        user_id=get_agent_id(context, member_id),
        removed_by=get_agent_id(context, user_id)
    )
    try:
        context.organization_handler.handle_remove_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


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
    assert view.entries[-1].timestamp is not None, "Last entry has no timestamp"


@then('the organization should have {count:d} members')
def step_check_member_count(context: Context, count: int):
    view = context.view_store.get_view(
        context.current_organization_id,
        OrganizationDetailsView
    )
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