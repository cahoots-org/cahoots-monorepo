from uuid import uuid4
from behave import given, when, then
from behave.runner import Context
from features.steps.common import ensure_agent_id


@given('a system user "{user_id}" exists')
def step_system_user_exists(context: Context, user_id: str):
    ensure_agent_id(context, user_id)


@then('the operation should be rejected with error "{error_message}"')
def step_check_error_message(context: Context, error_message: str):
    assert context.last_error == error_message, \
        f"Expected error '{error_message}', got '{context.last_error}'" 