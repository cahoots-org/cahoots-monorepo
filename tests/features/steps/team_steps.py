from uuid import uuid4
from behave import given, when, then
from behave.runner import Context
from tests.features.steps.common import ensure_agent_id

# Define command classes for team operations
class CreateTeam:
    def __init__(self, command_id, correlation_id, organization_id, name, description, created_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.organization_id = organization_id
        self.name = name
        self.description = description
        self.created_by = created_by

class AddTeamMember:
    def __init__(self, command_id, correlation_id, team_id, member_id, role, added_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.team_id = team_id
        self.member_id = member_id
        self.role = role
        self.added_by = added_by
        self.created_by = added_by

class UpdateTeamMemberRole:
    def __init__(self, command_id, correlation_id, team_id, member_id, new_role, reason, updated_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.team_id = team_id
        self.member_id = member_id
        self.new_role = new_role
        self.reason = reason
        self.updated_by = updated_by
        self.created_by = updated_by
        self.user_id = member_id

class RemoveTeamMember:
    def __init__(self, command_id, correlation_id, team_id, member_id, removed_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.team_id = team_id
        self.member_id = member_id
        self.removed_by = removed_by
        self.created_by = removed_by
        self.user_id = member_id

class ArchiveTeam:
    def __init__(self, command_id, correlation_id, team_id, reason, archived_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.team_id = team_id
        self.reason = reason
        self.archived_by = archived_by

class TransferTeamLeadership:
    def __init__(self, command_id, correlation_id, team_id, new_lead_id, transferred_by):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.team_id = team_id
        self.new_lead_id = new_lead_id
        self.transferred_by = transferred_by
        self.created_by = transferred_by

# Define view classes
class TeamView:
    def __init__(self, team_id):
        self.team_id = team_id
        self.name = ""
        self.members = {}
        self.status = "active"
        self.last_notification = None

class TeamMembersView:
    def __init__(self, team_id):
        self.team_id = team_id
        self.members = {}

# Import events from team module
from cahoots_events.team import (
    TeamCreated, TeamMemberAdded, TeamMemberRoleChanged,
    TeamMemberRemoved, TeamArchived, TeamLeadershipTransferred
)

@when('agent "{agent_id}" creates a team')
def step_create_team(context: Context, agent_id: str):
    row = context.table[0]
    cmd = CreateTeam(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        name=row['name'],
        description=row['description'],
        created_by=ensure_agent_id(context, agent_id)
    )
    events = context.organization_handler.handle_create_team(cmd)
    context.current_team_id = events[0].team_id

@then('the team should be created successfully')
def step_check_team_created(context: Context):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert view is not None, "Team not created"
    assert view.name != '', "Team name is empty"

@then('the team details should show')
def step_check_team_details(context: Context):
    row = context.table[0]
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert view.name == row['name'], \
        f"Expected team name {row['name']}, got {view.name}"
    assert len(view.members) == int(row['member_count']), \
        f"Expected {row['member_count']} members, got {len(view.members)}"

@given('a team "{team_name}" exists')
def step_team_exists(context: Context, team_name: str):
    cmd = CreateTeam(
        command_id=uuid4(),
        correlation_id=uuid4(),
        organization_id=context.current_organization_id,
        name=team_name,
        description=f"{team_name} description",
        created_by=ensure_agent_id(context, 'admin-1')
    )
    events = context.organization_handler.handle_create_team(cmd)
    context.current_team_id = events[0].team_id

@when('agent "{agent_id}" adds member "{member_id}" to the team')
def step_add_team_member(context: Context, agent_id: str, member_id: str):
    row = context.table[0]
    cmd = AddTeamMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        member_id=ensure_agent_id(context, member_id),
        role=row['role'],
        added_by=ensure_agent_id(context, agent_id)
    )
    context.organization_handler.handle_add_team_member(cmd)

@then('the team should have {count:d} members')
def step_check_team_members(context: Context, count: int):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert len(view.members) == count, \
        f"Expected {count} members, got {len(view.members)}"

@then('agent "{agent_id}" should have role "{role}" in the team')
def step_check_member_role(context: Context, agent_id: str, role: str):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    member_id = ensure_agent_id(context, agent_id)
    assert member_id in view.members, f"Member {agent_id} not found in team"
    assert view.members[member_id]['role'] == role, \
        f"Expected role {role}, got {view.members[member_id]['role']}"

@given('agent "{agent_id}" is a lead of the team')
def step_member_is_lead(context: Context, agent_id: str):
    # Get the current lead from the team view
    team_view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    current_lead = None
    for member_id, member in team_view.members.items():
        if member['role'] == 'lead':
            current_lead = member_id
            break

    if not current_lead:
        raise ValueError("No current lead found")

    cmd = AddTeamMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        member_id=ensure_agent_id(context, agent_id),
        role='lead',
        added_by=current_lead
    )
    context.organization_handler.handle_add_team_member(cmd)

@given('agent "{agent_id}" is a member of the team')
def step_member_exists(context: Context, agent_id: str):
    # Get the current lead from the team view
    team_view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    current_lead = None
    for member_id, member in team_view.members.items():
        if member['role'] == 'lead':
            current_lead = member_id
            break

    if not current_lead:
        raise ValueError("No current lead found")

    cmd = AddTeamMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        member_id=ensure_agent_id(context, agent_id),
        role='developer',
        added_by=current_lead
    )
    context.organization_handler.handle_add_team_member(cmd)

@when('agent "{agent_id}" updates member "{member_id}" role')
def step_update_member_role(context: Context, agent_id: str, member_id: str):
    row = context.table[0]
    cmd = UpdateTeamMemberRole(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        member_id=ensure_agent_id(context, member_id),
        new_role=row['new_role'],
        reason=row['reason'],
        updated_by=ensure_agent_id(context, agent_id)
    )
    context.organization_handler.handle_update_team_member_role(cmd)

@when('agent "{agent_id}" removes member "{member_id}" from the team')
def step_remove_team_member(context: Context, agent_id: str, member_id: str):
    cmd = RemoveTeamMember(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        member_id=ensure_agent_id(context, member_id),
        removed_by=ensure_agent_id(context, agent_id)
    )
    context.organization_handler.handle_remove_team_member(cmd)

@then('agent "{agent_id}" should not be a member of the team')
def step_check_member_removed(context: Context, agent_id: str):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    member_id = ensure_agent_id(context, agent_id)
    assert member_id not in view.members, \
        f"Member {agent_id} still in team"

@when('agent "{agent_id}" transfers leadership to "{new_lead_id}"')
def step_transfer_leadership(context: Context, agent_id: str, new_lead_id: str):
    cmd = TransferTeamLeadership(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        new_lead_id=ensure_agent_id(context, new_lead_id),
        transferred_by=ensure_agent_id(context, agent_id)
    )
    context.organization_handler.handle_transfer_team_leadership(cmd)

@when('agent "{agent_id}" attempts to add member "{member_id}" to the team')
def step_attempt_add_member(context: Context, agent_id: str, member_id: str):
    row = context.table[0]
    try:
        cmd = AddTeamMember(
            command_id=uuid4(),
            correlation_id=uuid4(),
            team_id=context.current_team_id,
            member_id=ensure_agent_id(context, member_id),
            role=row['role'],
            added_by=ensure_agent_id(context, agent_id)
        )
        context.organization_handler.handle_add_team_member(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@when('agent "{agent_id}" archives the team')
def step_archive_team(context: Context, agent_id: str):
    row = context.table[0]
    cmd = ArchiveTeam(
        command_id=uuid4(),
        correlation_id=uuid4(),
        team_id=context.current_team_id,
        reason=row['reason'],
        archived_by=ensure_agent_id(context, agent_id)
    )
    context.organization_handler.handle_archive_team(cmd)

@then('the team should be archived')
def step_check_team_archived(context: Context):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert view.status == 'archived', "Team not archived"

@then('team members should be notified')
def step_check_members_notified(context: Context):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert view.last_notification is not None, "No notification sent"
    assert view.last_notification['type'] == 'team_archived', \
        "Wrong notification type"

@then('the team should have 1 member')
def step_check_one_member(context: Context):
    view = context.view_store.get_view(
        context.current_team_id,
        TeamView
    )
    assert len(view.members) == 1, \
        f"Expected 1 member, got {len(view.members)}" 