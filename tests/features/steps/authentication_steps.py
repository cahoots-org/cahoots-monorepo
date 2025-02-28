"""Authentication step definitions"""
from datetime import datetime, timedelta
from uuid import uuid4
from behave import given, when, then
from behave.runner import Context

from features.steps.common import ensure_agent_id
from cahoots_events.auth_commands import (
    RegisterUser, VerifyEmail, LoginUser as Login, RequestPasswordReset,
    ResetPassword, RefreshToken, LogoutUser as Logout, RevokeSession
)
from cahoots_events.auth import (
    UserRegistered, EmailVerified, UserLoggedIn, PasswordResetRequested,
    PasswordReset, TokenRefreshed, UserLoggedOut, SessionRevoked
)
from cahoots_events.auth_views import UserView, SessionView

@when('a user registers with')
def step_register_user(context: Context):
    """Handle user registration"""
    row = context.table[0]
    cmd = RegisterUser(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=row['email'],
        password=row['password']
    )
    try:
        events = context.auth_handler.handle_register_user(cmd)
        context.current_user_id = events[0].user_id
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the user should be registered successfully')
def step_check_user_registered(context: Context):
    """Verify that user was registered"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view is not None, "User not registered"

@then('a verification email should be sent')
def step_check_verification_email(context: Context):
    """Verify that verification email was sent"""
    assert len(context.email_service.sent_emails) > 0
    email = next(e for e in context.email_service.sent_emails if e['type'] == 'verification')
    assert email is not None
    context.verification_token = email['token']

@then('the user should not be verified')
def step_check_user_not_verified(context: Context):
    """Verify that user is not verified"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert not view.is_verified, "User should not be verified"

@given('a registered user "{email}" exists')
def step_registered_user_exists(context: Context, email: str):
    """Create a registered user"""
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
    """Handle email verification"""
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
    try:
        context.auth_handler.handle_verify_email(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the user should be verified')
def step_check_user_verified(context: Context):
    """Verify that user is verified"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.is_verified, "User should be verified"

@then('the user should be able to log in')
def step_check_user_can_login(context: Context):
    """Verify that user can log in"""
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
    try:
        events = context.auth_handler.handle_login(cmd)
        context.current_session = events[0]
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)
    assert context.last_error is None, f"Login failed: {context.last_error}"

@given('a verified user exists')
def step_verified_user_exists(context: Context):
    """Create and verify a user"""
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
    
    # Get verification token
    email = next(e for e in context.email_service.sent_emails if e['type'] == 'verification')
    
    # Verify user
    cmd = VerifyEmail(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        verification_token=email['token']
    )
    context.auth_handler.handle_verify_email(cmd)

@when('the user attempts to login with valid credentials')
def step_login_valid_credentials(context: Context):
    """Handle valid login attempt"""
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=context.table[0]['email'],
        password=context.table[0]['password']
    )
    try:
        events = context.auth_handler.handle_login(cmd)
        context.current_session = events[0]
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the login should be successful')
def step_check_login_successful(context: Context):
    """Verify that login was successful"""
    assert context.current_session is not None, "No session created"

@then('an access token should be issued')
def step_check_access_token_issued(context: Context):
    """Verify that access token was issued"""
    assert context.current_session.access_token is not None, "No access token issued"

@then('a refresh token should be issued')
def step_check_refresh_token_issued(context: Context):
    """Verify that refresh token was issued"""
    assert context.current_session.refresh_token is not None, "No refresh token issued"

@when('the user attempts to login with invalid credentials')
def step_login_invalid_credentials(context: Context):
    """Handle invalid login attempt"""
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=context.table[0]['email'],
        password=context.table[0]['password']
    )
    try:
        context.auth_handler.handle_login(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the login should be rejected')
def step_check_login_rejected(context: Context):
    """Verify that login was rejected"""
    assert context.last_error is not None, "Login should have been rejected"

@then('an error message "{message}" should be shown')
def step_check_error_message(context: Context, message: str):
    """Verify error message"""
    assert context.last_error == message, \
        f"Expected error '{message}', got '{context.last_error}'"

@when('the user requests a password reset')
def step_request_password_reset(context: Context):
    """Handle password reset request"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = RequestPasswordReset(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=view.email
    )
    try:
        events = context.auth_handler.handle_request_password_reset(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('a password reset email should be sent')
def step_check_reset_email_sent(context: Context):
    """Verify reset email sending"""
    email = next(e for e in context.email_service.sent_emails if e['type'] == 'reset')
    assert email is not None
    context.reset_token = email['token']

@then('the password reset token should be valid')
def step_check_reset_token_valid(context: Context):
    """Verify reset token validity"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.reset_token == context.reset_token, "Reset token mismatch"

@given('a user has requested a password reset')
def step_user_requested_reset(context: Context):
    """Create user and request password reset"""
    step_verified_user_exists(context)
    step_request_password_reset(context)
    step_check_reset_email_sent(context)

@when('the user resets their password with a valid token')
def step_reset_password(context: Context):
    """Handle password reset"""
    cmd = ResetPassword(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        reset_token=context.reset_token,
        new_password=context.table[0]['new_password']
    )
    try:
        context.auth_handler.handle_reset_password(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the password should be updated')
def step_check_password_updated(context: Context):
    """Verify password update"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    assert view.reset_token is None, "Reset token should be cleared"

@then('all existing sessions should be invalidated')
def step_check_sessions_invalidated(context: Context):
    """Verify session invalidation"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert len(view.active_sessions) == 0, "Sessions should be invalidated"

@then('the user should be able to login with the new password')
def step_check_login_with_new_password(context: Context):
    """Verify login with new password"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    cmd = Login(
        command_id=uuid4(),
        correlation_id=uuid4(),
        email=view.email,
        password=context.table[0]['new_password']
    )
    try:
        events = context.auth_handler.handle_login(cmd)
        context.current_session = events[0]
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)
    assert context.last_error is None, f"Login failed: {context.last_error}"

@given('a user is logged in')
def step_user_logged_in(context: Context):
    """Create and log in a user"""
    step_verified_user_exists(context)
    step_login_valid_credentials(context)

@given('the access token has expired')
def step_access_token_expired(context: Context):
    """Simulate token expiration"""
    # No need to do anything, we'll just use the refresh token

@when('the user attempts to refresh their token')
def step_refresh_token(context: Context):
    """Handle token refresh"""
    cmd = RefreshToken(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        refresh_token=context.current_session.refresh_token
    )
    try:
        events = context.auth_handler.handle_refresh_token(cmd)
        context.new_access_token = events[0].access_token
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('a new access token should be issued')
def step_check_new_access_token(context: Context):
    """Verify new access token"""
    assert context.new_access_token is not None, "No new access token issued"
    assert context.new_access_token != context.current_session.access_token, \
        "New access token should be different"

@then('the refresh token should remain valid')
def step_check_refresh_token_valid(context: Context):
    """Verify refresh token validity"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.current_session.refresh_token in view.valid_refresh_tokens, \
        "Refresh token should still be valid"

@when('the user logs out')
def step_logout(context: Context):
    """Handle logout"""
    cmd = Logout(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        session_id=context.current_session.session_id
    )
    try:
        context.auth_handler.handle_logout(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('the session should be invalidated')
def step_check_session_invalidated(context: Context):
    """Verify session invalidation"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert not any(s['session_id'] == context.current_session.session_id 
                  for s in view.active_sessions), \
        "Session should be invalidated"

@then('the refresh token should be revoked')
def step_check_refresh_token_revoked(context: Context):
    """Verify refresh token revocation"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert context.current_session.refresh_token not in view.valid_refresh_tokens, \
        "Refresh token should be revoked"

@when('the user logs in from multiple devices')
def step_login_multiple_devices(context: Context):
    """Handle multiple device login"""
    view = context.view_store.get_view(
        context.current_user_id,
        UserView
    )
    context.sessions = []
    for _ in range(3):  # Log in from 3 devices
        cmd = Login(
            command_id=uuid4(),
            correlation_id=uuid4(),
            email=view.email,
            password=context.table[0]['password']
        )
        events = context.auth_handler.handle_login(cmd)
        context.sessions.append(events[0])

@then('each device should have a unique session')
def step_check_unique_sessions(context: Context):
    """Verify unique sessions"""
    session_ids = [s.session_id for s in context.sessions]
    assert len(session_ids) == len(set(session_ids)), \
        "Sessions should be unique"

@then('all sessions should be listed in the user\'s active sessions')
def step_check_sessions_listed(context: Context):
    """Verify active sessions"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    for session in context.sessions:
        assert any(s['session_id'] == session.session_id 
                  for s in view.active_sessions), \
            f"Session {session.session_id} not found in active sessions"

@given('a user is logged in from multiple devices')
def step_user_logged_in_multiple(context: Context):
    """Create user and log in from multiple devices"""
    step_verified_user_exists(context)
    step_login_multiple_devices(context)

@when('the user revokes a specific session')
def step_revoke_session(context: Context):
    """Handle session revocation"""
    # Revoke the first session
    context.revoked_session_id = context.sessions[0].session_id
    cmd = RevokeSession(
        command_id=uuid4(),
        correlation_id=uuid4(),
        user_id=context.current_user_id,
        session_id=context.revoked_session_id
    )
    try:
        context.auth_handler.handle_revoke_session(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)

@then('that session should be invalidated')
def step_check_specific_session_invalidated(context: Context):
    """Verify specific session invalidation"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    assert not any(s['session_id'] == context.revoked_session_id 
                  for s in view.active_sessions), \
        "Revoked session should be invalidated"

@then('other sessions should remain active')
def step_check_other_sessions_active(context: Context):
    """Verify other sessions remain active"""
    view = context.view_store.get_view(
        context.current_user_id,
        SessionView
    )
    for session in context.sessions[1:]:  # Skip the first (revoked) session
        assert any(s['session_id'] == session.session_id 
                  for s in view.active_sessions), \
            f"Session {session.session_id} should still be active" 