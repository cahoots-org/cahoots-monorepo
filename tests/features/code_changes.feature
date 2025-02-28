Feature: Code Change Workflows
  As a development team
  We want to manage code changes through a structured workflow
  So that we can maintain code quality and traceability

  Background:
    Given a new project "Test Project" is created
    And a requirement "Login Feature" is added to the project
    And a task "Implement OAuth Flow" is created for the requirement

  Scenario: Successfully propose and implement a code change
    When agent "dev-1" proposes a code change
      | files          | description        | reasoning                    |
      | auth/login.py  | Add OAuth support  | Required for SSO integration |
    Then the code change should be in "proposed" status
    And the code change should be visible in the project's pending changes

    When agent "reviewer-1" reviews the code change
      | status    | comments                          |
      | approved  | Implementation looks good to me    |
    Then the code change should be in "approved" status

    When agent "dev-1" implements the approved change
    Then the code change should be in "implemented" status
    And the code change should be visible in the project's implemented changes

  Scenario: Reject a code change that needs improvements
    When agent "dev-2" proposes a code change
      | files          | description          | reasoning               |
      | auth/users.py  | Update user model    | Add required fields     |
    Then the code change should be in "proposed" status

    When agent "reviewer-1" reviews the code change
      | status             | comments                    | suggested_changes                    |
      | changes_requested  | Missing validation logic    | Add input validation in users.py:25  |
    Then the code change should be in "changes_requested" status
    And the code change should have review comments

  Scenario: Prevent self-review of code changes
    When agent "dev-3" proposes a code change
      | files          | description        | reasoning          |
      | auth/token.py  | Add token refresh  | Improve security   |
    Then the code change should be in "proposed" status

    When agent "dev-3" attempts to review their own code change
    Then the review should be rejected with error "Code change cannot be reviewed"

  Scenario: Track multiple changes to the same file
    When agent "dev-1" proposes a code change
      | files          | description        | reasoning          |
      | auth/login.py  | Fix login timeout  | Bug fix           |
    And agent "dev-2" proposes a code change
      | files          | description        | reasoning          |
      | auth/login.py  | Add rate limiting  | Security fix      |
    Then there should be 2 pending changes for file "auth/login.py" 