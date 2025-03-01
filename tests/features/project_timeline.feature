Feature: Project Timeline and Status Management
  As a project manager
  I want to manage project timelines and status
  So that I can track progress and handle blockers effectively

  Background:
    Given a new project "Mobile App" is created
    And a requirement "User Authentication" is added to the project
    And a task "Implement Login UI" is created for the requirement

  Scenario: Set project timeline with milestones
    When agent "pm-1" sets the project timeline
      | start_date  | target_date | milestone_date | milestone_description     |
      | 2024-03-01 | 2024-06-30  | 2024-04-15    | Authentication Complete   |
    Then the project timeline should be set
    And the milestone "Authentication Complete" should be scheduled for "2024-04-15"

  Scenario: Update project status with reason
    When agent "pm-1" updates project status to "in_progress"
      | reason                                  |
      | Development team onboarding completed   |
    Then the project status should be "in_progress"

  Scenario: Block and unblock requirements
    When agent "dev-1" blocks the requirement
      | blocker_description                           |
      | Waiting for third-party API documentation     |
    Then the requirement should be blocked
    And the requirement should show the blocker description

    When agent "pm-1" unblocks the requirement
      | resolution                          |
      | API documentation now available     |
    Then the requirement should be active

  Scenario: Change requirement priorities
    When agent "pm-1" adds a requirement
      | title           | description              | priority |
      | Push Messages   | Implement notifications  | low      |
    And agent "pm-1" changes requirement priority
      | requirement     | new_priority | reason                    |
      | Push Messages   | high         | Critical for MVP launch   |
    Then the requirement "Push Messages" should have priority "high"

  Scenario: Assign and track task status
    When agent "pm-1" assigns the task to "dev-2"
    Then the task should be assigned to "dev-2"

    When agent "dev-2" blocks the task
      | blocker_description                     |
      | Dependency package version conflict     |
    Then the task should be blocked
    And the task should show the blocker description

    When agent "dev-2" unblocks the task
      | resolution                    |
      | Updated package versions      |
    Then the task should be active

  Scenario: Prevent completing blocked requirement
    Given a requirement "Payment Integration" is added to the project
    When agent "dev-1" blocks the requirement
      | blocker_description                   |
      | Awaiting payment gateway credentials  |
    And agent "pm-1" attempts to complete the requirement
    Then the operation should be rejected with error "Cannot complete blocked requirement"

  Scenario: Track task priorities
    When agent "pm-1" creates a task
      | title             | description          | complexity |
      | Error Handling    | Add error states     | medium     |
    And agent "pm-1" changes task priority
      | task            | new_priority | reason                        |
      | Error Handling  | high         | Critical for user experience  |
    Then the task "Error Handling" should have priority "high"

  Scenario: Complete project with all requirements done
    Given all requirements are completed
    When agent "pm-1" updates project status to "completed"
      | reason                            |
      | All requirements implemented      |
    Then the project status should be "completed"

  Scenario: Prevent completing project with active requirements
    Given a new requirement "Analytics" is added to the project
    When agent "pm-1" attempts to update project status to "completed"
      | reason                    |
      | Project deadline reached  |
    Then the operation should be rejected with error "Cannot complete project with active requirements" 