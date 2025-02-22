Feature: Authentication and Authorization
  As a system user
  I want to authenticate and manage access
  So that I can securely access the system

  Scenario: Register new user
    When a user registers with
      | email                 | password  | name          |
      | user@example.com      | pass123!  | John Doe      |
    Then the user should be registered successfully
    And a verification email should be sent
    And the user should not be verified

  Scenario: Verify email
    Given a registered user "user@example.com" exists
    When the user verifies their email with the verification token
    Then the user should be verified
    And the user should be able to log in

  Scenario: Login with valid credentials
    Given a verified user exists
      | email                 | password  |
      | user@example.com      | pass123!  |
    When the user attempts to login with valid credentials
    Then the login should be successful
    And an access token should be issued
    And a refresh token should be issued

  Scenario: Login with invalid credentials
    Given a verified user exists
      | email                 | password  |
      | user@example.com      | pass123!  |
    When the user attempts to login with invalid credentials
      | email                 | password  |
      | user@example.com      | wrong!    |
    Then the login should be rejected
    And an error message "Invalid credentials" should be shown

  Scenario: Reset password request
    Given a verified user exists
      | email                 | password  |
      | user@example.com      | pass123!  |
    When the user requests a password reset
    Then a password reset email should be sent
    And the password reset token should be valid

  Scenario: Reset password
    Given a user has requested a password reset
    When the user resets their password with a valid token
      | new_password |
      | newPass123!  |
    Then the password should be updated
    And all existing sessions should be invalidated
    And the user should be able to login with the new password

  Scenario: Refresh access token
    Given a user is logged in
    And the access token has expired
    When the user attempts to refresh their token
    Then a new access token should be issued
    And the refresh token should remain valid

  Scenario: Logout
    Given a user is logged in
    When the user logs out
    Then the session should be invalidated
    And the refresh token should be revoked

  Scenario: Multiple device login
    Given a verified user exists
      | email                 | password  |
      | user@example.com      | pass123!  |
    When the user logs in from multiple devices
    Then each device should have a unique session
    And all sessions should be listed in the user's active sessions

  Scenario: Revoke specific session
    Given a user is logged in from multiple devices
    When the user revokes a specific session
    Then that session should be invalidated
    And other sessions should remain active 