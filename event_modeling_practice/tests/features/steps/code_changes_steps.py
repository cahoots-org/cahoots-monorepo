from uuid import uuid4
from behave import when, then
from behave.runner import Context

from tests.features.steps.common import ensure_agent_id
from sdlc.domain.code_changes.commands import (
    ProposeCodeChange, ReviewCodeChange, ImplementCodeChange
)
from sdlc.domain.code_changes.views import CodeChangesView

@when('agent "{agent_id}" proposes a code change')
def step_propose_code_change(context: Context, agent_id: str):
    row = context.table[0]
    cmd = ProposeCodeChange(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        files=row['files'].split(','),
        description=row['description'],
        reasoning=row['reasoning'],
        proposed_by=ensure_agent_id(context, agent_id)
    )
    events = context.project_handler.handle_propose_code_change(cmd)
    context.current_change_id = events[0].change_id

@then('the code change should be in "{status}" status')
def step_check_code_change_status(context: Context, status: str):
    view = context.view_store.get_view(
        context.current_project_id,
        CodeChangesView
    )
    change = view.changes[context.current_change_id]
    assert change['status'] == status, \
        f"Expected status {status}, got {change['status']}"

@then('the code change should be visible in the project\'s pending changes')
def step_check_pending_changes(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        CodeChangesView
    )
    assert context.current_change_id in view.pending_changes, \
        "Change not found in pending changes"

@when('agent "{agent_id}" reviews the code change')
def step_review_code_change(context: Context, agent_id: str):
    row = context.table[0]
    cmd = ReviewCodeChange(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        change_id=context.current_change_id,
        status=row['status'],
        comments=row['comments'],
        suggested_changes=row.get('suggested_changes', ''),
        reviewed_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_review_code_change(cmd)

@when('agent "{agent_id}" implements the approved change')
def step_implement_code_change(context: Context, agent_id: str):
    cmd = ImplementCodeChange(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        change_id=context.current_change_id,
        implemented_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_implement_code_change(cmd)

@then('the code change should be visible in the project\'s implemented changes')
def step_check_implemented_changes(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        CodeChangesView
    )
    assert context.current_change_id in view.implemented_changes, \
        "Change not found in implemented changes"

@then('the code change should have review comments')
def step_check_review_comments(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        CodeChangesView
    )
    change = view.changes[context.current_change_id]
    assert change['comments'] != '', "No review comments found"
    assert change['suggested_changes'] != '', "No suggested changes found"

@when('agent "{agent_id}" attempts to review their own code change')
def step_attempt_self_review(context: Context, agent_id: str):
    try:
        cmd = ReviewCodeChange(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            change_id=context.current_change_id,
            status='approved',
            comments='Self review',
            suggested_changes='',
            reviewed_by=ensure_agent_id(context, agent_id)
        )
        context.project_handler.handle_review_code_change(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('there should be {count:d} pending changes for file "{file_path}"')
def step_check_file_pending_changes(context: Context, count: int, file_path: str):
    view = context.view_store.get_view(
        context.current_project_id,
        CodeChangesView
    )
    file_changes = [
        change for change in view.pending_changes.values()
        if file_path in change['files']
    ]
    assert len(file_changes) == count, \
        f"Expected {count} pending changes for {file_path}, got {len(file_changes)}"

@then('the review should be rejected with error "Code change cannot be reviewed"')
def step_check_review_rejected(context: Context):
    assert context.last_error == "Code change cannot be reviewed by the proposer", \
        f"Expected error 'Code change cannot be reviewed by the proposer', got '{context.last_error}'" 