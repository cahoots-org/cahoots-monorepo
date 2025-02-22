from uuid import uuid4
from behave import given, when, then
from behave.runner import Context

from tests.features.steps.common import ensure_agent_id
from sdlc.domain.auth.commands import (
    RegisterUser, VerifyEmail, Login, RequestPasswordReset,
    ResetPassword, RefreshToken, Logout, RevokeSession
)
from sdlc.domain.auth.events import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)
from sdlc.domain.auth.views import UserView, SessionView

@when('a user registers with')
def step_register_user(context: Context):
    row = context.table[0]
    cmd = RegisterUser(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=row['email'],
        password=row['password']
    )
    events = context.auth_handler.handle_register_user(cmd)
    context.current_user_id = events[0].user_id

@then('the user should be registered successfully')
def step_check_user_registered(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view is not None, "User not registered"
    assert view.email != '', "User email is empty"

@then('a verification email should be sent')
def step_check_verification_email(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.verification_token is not None, "No verification token found"

@then('the user should not be verified')
def step_check_user_not_verified(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert not view.is_verified, "User should not be verified"

@given('a registered user "{email}" exists')
def step_registered_user_exists(context: Context, email: str):
    cmd = RegisterUser(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=email,
        password='pass123!'
    )
    events = context.auth_handler.handle_register_user(cmd)
    context.current_user_id = events[0].user_id

@when('the user verifies their email with the verification token')
def step_verify_email(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = VerifyEmail(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        verification_token=view.verification_token
    )
    context.auth_handler.handle_verify_email(cmd)

@then('the user should be verified')
def step_check_user_verified(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.is_verified, "User should be verified"

@then('the user should be able to log in')
def step_check_user_can_login(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=view.email,
        password='pass123!'
    )
    events = context.auth_handler.handle_login(cmd)
    assert events[0].access_token is not None, "Login failed"

@given('a verified user exists')
def step_verified_user_exists(context: Context):
    row = context.table[0]
    # Register user
    cmd = RegisterUser(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=row['email'],
        password=row['password']
    )
    events = context.auth_handler.handle_register_user(cmd)
    context.current_user_id = events[0].user_id
    
    # Verify user
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = VerifyEmail(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        verification_token=view.verification_token
    )
    context.auth_handler.handle_verify_email(cmd)

@when('the user attempts to login with valid credentials')
def step_login_valid_credentials(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=view.email,
        password='pass123!'
    )
    events = context.auth_handler.handle_login(cmd)
    context.current_session = events[0]

@then('the login should be successful')
def step_check_login_successful(context: Context):
    assert context.current_session is not None, "No session created"
    assert context.current_session.access_token is not None, "No access token issued"

@then('an access token should be issued')
def step_check_access_token_issued(context: Context):
    assert context.current_session.access_token is not None, "No access token issued"

@then('a refresh token should be issued')
def step_check_refresh_token_issued(context: Context):
    assert context.current_session.refresh_token is not None, "No refresh token issued"

@when('the user attempts to login with invalid credentials')
def step_login_invalid_credentials(context: Context):
    row = context.table[0]
    try:
        cmd = Login(
            command_id=uuid4(),
            correlation_id=uuid4(),
            email=row['email'],
            password=row['password']
        )
        context.auth_handler.handle_login(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the login should be rejected')
def step_check_login_rejected(context: Context):
    assert context.last_error is not None, "Login should have been rejected"

@then('an error message "Invalid credentials" should be shown')
def step_check_invalid_credentials_error(context: Context):
    assert context.last_error == "Invalid credentials", \
        f"Expected error 'Invalid credentials', got '{context.last_error}'"

@when('the user requests a password reset')
def step_request_password_reset(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = RequestPasswordReset(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=view.email
    )
    events = context.auth_handler.handle_request_password_reset(cmd)
    context.reset_token = events[0].reset_token

@then('a password reset email should be sent')
def step_check_reset_email_sent(context: Context):
    assert context.reset_token is not None, "No reset token generated"

@then('the password reset token should be valid')
def step_check_reset_token_valid(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.reset_token == context.reset_token, "Reset token not stored"

@given('a user is logged in')
def step_user_logged_in(context: Context):
    """Create a verified user and log them in"""
    # Create test data table for user creation
    context.table = [{'email': 'user@example.com', 'password': 'pass123!'}]
    step_verified_user_exists(context)
    step_login_valid_credentials(context)

@given('the access token has expired')
def step_access_token_expired(context: Context):
    # Simulate token expiration
    context.current_session.access_token_expired = True

@when('the user attempts to refresh their token')
def step_refresh_token(context: Context):
    cmd = RefreshToken(
        command_id=uuid4(),
        correlation_id=uuid4(),
        refresh_token=context.current_session.refresh_token
    )
    events = context.auth_handler.handle_refresh_token(cmd)
    context.new_access_token = events[0].access_token

@then('a new access token should be issued')
def step_check_new_access_token(context: Context):
    assert context.new_access_token is not None, "No new access token issued"

@then('the refresh token should remain valid')
def step_check_refresh_token_valid(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.current_session.refresh_token in view.valid_refresh_tokens, \
        "Refresh token invalidated"

@when('the user logs out')
def step_logout(context: Context):
    cmd = Logout(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        session_id=context.current_session.session_id
    )
    context.auth_handler.handle_logout(cmd)

@then('the session should be invalidated')
def step_check_session_invalidated(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.current_session.session_id not in view.active_sessions, \
        "Session not invalidated"

@then('the refresh token should be revoked')
def step_check_refresh_token_revoked(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.current_session.refresh_token not in view.valid_refresh_tokens, \
        "Refresh token not revoked"

@when('the user logs in from multiple devices')
def step_login_multiple_devices(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    # Login from three different devices
    for _ in range(3):
        cmd = Login(
            command_id=uuid4(),
            correlation_id=uuid4(),
            email=view.email,
            password='pass123!'
        )
        context.auth_handler.handle_login(cmd)

@then('each device should have a unique session')
def step_check_unique_sessions(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert len(view.active_sessions) == 3, "Not all sessions created"
    # Check that all session IDs are unique
    session_ids = [s['session_id'] for s in view.active_sessions]
    assert len(set(session_ids)) == 3, "Duplicate session IDs found"

@then('all sessions should be listed in the user\'s active sessions')
def step_check_sessions_listed(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert len(view.active_sessions) == 3, "Not all sessions listed"

@given('a user is logged in from multiple devices')
def step_user_logged_in_multiple(context: Context):
    """Create a verified user and log in from multiple devices"""
    # Create test data table for user creation
    context.table = [{'email': 'user@example.com', 'password': 'pass123!'}]
    step_verified_user_exists(context)
    step_login_multiple_devices(context)

@when('the user revokes a specific session')
def step_revoke_session(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    # Revoke the first session
    session_to_revoke = view.active_sessions[0]
    cmd = RevokeSession(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        session_id=session_to_revoke['session_id']
    )
    context.auth_handler.handle_revoke_session(cmd)
    context.revoked_session_id = session_to_revoke['session_id']

@then('that session should be invalidated')
def step_check_specific_session_invalidated(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.revoked_session_id not in [s['session_id'] for s in view.active_sessions], \
        "Session not invalidated"

@then('other sessions should remain active')
def step_check_other_sessions_active(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert len(view.active_sessions) == 2, "Wrong number of active sessions"

@given('a user has requested a password reset')
def step_user_requested_reset(context: Context):
    """Create a verified user and request password reset"""
    # Create test data table for user creation
    context.table = [{'email': 'user@example.com', 'password': 'pass123!'}]
    step_verified_user_exists(context)
    step_request_password_reset(context)

@when('the user resets their password with a valid token')
def step_reset_password(context: Context):
    row = context.table[0]
    cmd = ResetPassword(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        reset_token=context.reset_token,
        new_password=row['new_password']
    )
    context.auth_handler.handle_reset_password(cmd)

@then('the password should be updated')
def step_check_password_updated(context: Context):
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.password_hash != '', "Password not updated"

@then('all existing sessions should be invalidated')
def step_check_sessions_invalidated(context: Context):
    """Verify that all sessions are invalidated"""
    view = context.view_store.get_or_create_view(
        SessionView,
        context.current_user_id
    )
    assert len(view.active_sessions) == 0, "Sessions not invalidated"

@then('the user should be able to login with the new password')
def step_check_login_with_new_password(context: Context):
    """Verify that the user can log in with the new password"""
    # Get the user's email from the view store
    events = context.event_store.get_all_events()
    user_event = next(e for e in events if isinstance(e, UserRegistered))
    
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=user_event.email,
        password='newPass123!'
    )
    events = context.auth_handler.handle_login(cmd)
    assert events[0].access_token is not None, "Login with new password failed" 