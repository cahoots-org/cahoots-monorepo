Feature: Team Management
  As a team administrator
  I want to manage teams and their members
  So that I can organize work and collaboration effectively

  Background:
    Given an organization "Acme Corp" exists
    And agent "admin-1" is an admin of the organization
    And a system user "lead-1" exists
    And a system user "dev-1" exists

  Scenario: Create a new team
    When agent "admin-1" creates a team
      | name          | description             |
      | Backend Team  | Core Services Team      |
    Then the team should be created successfully
    And the team details should show
      | name          | member_count |
      | Backend Team  | 1            |
    And agent "admin-1" should have role "lead" in the team

  Scenario: Add team lead
    Given a team "Backend Team" exists
    When agent "admin-1" adds member "lead-1" to the team
      | role      |
      | lead      |
    Then the team should have 2 members
    And agent "lead-1" should have role "lead" in the team

  Scenario: Add team member
    Given a team "Backend Team" exists
    And agent "lead-1" is a lead of the team
    When agent "lead-1" adds member "dev-1" to the team
      | role        |
      | developer   |
    Then the team should have 3 members
    And agent "dev-1" should have role "developer" in the team

  Scenario: Update team member role
    Given a team "Backend Team" exists
    And agent "lead-1" is a lead of the team
    And agent "dev-1" is a member of the team
    When agent "lead-1" updates member "dev-1" role
      | new_role    | reason                    |
      | senior      | Promotion based on merit  |
    Then agent "dev-1" should have role "senior" in the team

  Scenario: Remove team member
    Given a team "Backend Team" exists
    And agent "lead-1" is a lead of the team
    And agent "dev-1" is a member of the team
    When agent "lead-1" removes member "dev-1" from the team
    Then the team should have 2 members
    And agent "dev-1" should not be a member of the team

  Scenario: Transfer team leadership
    Given a team "Backend Team" exists
    And agent "lead-1" is a lead of the team
    And agent "dev-1" is a member of the team
    When agent "lead-1" transfers leadership to "dev-1"
    Then agent "dev-1" should have role "lead" in the team
    And agent "lead-1" should have role "member" in the team

  Scenario: Prevent non-lead from adding members
    Given a team "Backend Team" exists
    And agent "dev-1" is a member of the team
    And a system user "dev-2" exists
    When agent "dev-1" attempts to add member "dev-2" to the team
      | role        |
      | developer   |
    Then the operation should be rejected with error "Insufficient permissions"

  Scenario: Archive team
    Given a team "Backend Team" exists
    And agent "admin-1" is an admin of the organization
    When agent "admin-1" archives the team
      | reason                        |
      | Project completed            |
    Then the team should be archived
    And team members should be notified 