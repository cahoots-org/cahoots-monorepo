Feature: Project Management Workflows
  As a development team
  We want to manage projects and requirements effectively
  So that we can track and deliver work efficiently

  Scenario: Create a new project with initial requirements
    When agent "pm-1" creates a new project
      | name          | description             | repository          | tech_stack        |
      | Auth Service  | Authentication Service   | auth-service       | python,fastapi    |
    Then the project should be created successfully
    And the project overview should show
      | active_requirements | completed_requirements | active_tasks | completed_tasks |
      | 0                  | 0                      | 0            | 0              |

    When agent "pm-1" adds a requirement
      | title           | description                    | priority |
      | OAuth Support   | Implement OAuth2 with Google   | high     |
    Then the requirement should be added to the project
    And the project overview should show
      | active_requirements | completed_requirements | active_tasks | completed_tasks |
      | 1                  | 0                      | 0            | 0              |

  Scenario: Add dependent requirements
    Given a new project "API Gateway" is created
    When agent "pm-1" adds a requirement
      | title           | description                    | priority |
      | Rate Limiting   | Implement API rate limiting    | high     |
    And agent "pm-1" adds a requirement
      | title           | description                    | priority | dependencies    |
      | Usage Metrics   | Track API usage metrics        | medium   | Rate Limiting   |
    Then the requirement "Usage Metrics" should depend on "Rate Limiting"
    And the requirements should be ordered correctly

  Scenario: Complete a requirement with all tasks done
    Given a new project "User Service" is created
    And a requirement "User Profile" is added to the project
    When agent "pm-1" creates a task
      | title             | description              | complexity |
      | Profile Schema    | Define database schema   | medium     |
    And agent "pm-1" creates a task
      | title             | description              | complexity |
      | CRUD Endpoints    | Implement REST API       | high       |
    Then the requirement should have 2 active tasks
    
    When all tasks for requirement "User Profile" are completed
    Then the requirement should be marked as complete
    And the project overview should show
      | active_requirements | completed_requirements | active_tasks | completed_tasks |
      | 0                  | 1                      | 0            | 2              |

  Scenario: Prevent completing requirement with pending tasks
    Given a new project "Payment Service" is created
    And a requirement "Payment Processing" is added to the project
    When agent "pm-1" creates a task
      | title             | description              | complexity |
      | Payment Gateway   | Integrate with Stripe    | high       |
    And agent "pm-1" attempts to complete the requirement
    Then the operation should be rejected with error "Cannot complete requirement with pending tasks" 