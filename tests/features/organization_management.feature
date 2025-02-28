Feature: Organization Management
  As an organization administrator
  I want to manage organizations and their members
  So that I can control access and collaboration

  Background:
    Given a system user "admin-1" exists

  Scenario: Create a new organization
    When agent "admin-1" creates an organization
      | name          | description             |
      | Acme Corp     | Technology Solutions    |
    Then the organization should be created successfully
    And the organization details should show
      | name          | member_count |
      | Acme Corp     | 1            |
    And agent "admin-1" should be an admin of the organization

  Scenario: Update organization name
    Given an organization "Acme Corp" exists
    And agent "admin-1" is an admin of the organization
    When agent "admin-1" updates the organization name to "Acme Technologies"
      | reason                    |
      | Rebranding initiative     |
    Then the organization name should be "Acme Technologies"
    And the change should be recorded in the audit log

  Scenario: Add member to organization
    Given an organization "Acme Corp" exists
    And agent "admin-1" is an admin of the organization
    And a system user "user-1" exists
    When agent "admin-1" adds member "user-1" to the organization
      | role      |
      | developer |
    Then the organization should have 2 members
    And agent "user-1" should have role "developer" in the organization

  Scenario: Remove member from organization
    Given an organization "Acme Corp" exists
    And agent "admin-1" is an admin of the organization
    And agent "user-1" is a member of the organization
    When agent "admin-1" removes member "user-1" from the organization
    Then the organization should have 1 member
    And agent "user-1" should not be a member of the organization

  Scenario: Prevent removing last admin
    Given an organization "Acme Corp" exists
    And agent "admin-1" is the only admin of the organization
    When agent "admin-1" attempts to leave the organization
    Then the operation should be rejected with error "Cannot remove the last admin"

  Scenario: Add duplicate member
    Given an organization "Acme Corp" exists
    And agent "admin-1" is an admin of the organization
    And agent "user-1" is a member of the organization
    When agent "admin-1" attempts to add member "user-1" to the organization
      | role      |
      | developer |
    Then the operation should be rejected with error "User is already a member"

  Scenario: Non-admin cannot add members
    Given an organization "Acme Corp" exists
    And agent "user-1" is a member with role "developer"
    And a system user "user-2" exists
    When agent "user-1" attempts to add member "user-2" to the organization
      | role      |
      | developer |
    Then the operation should be rejected with error "Insufficient permissions" 