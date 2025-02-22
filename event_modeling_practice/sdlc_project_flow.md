# SDLC Project Management Event Flow

## Events
1. ProjectInitiated
   - projectId: UUID
   - name: String
   - description: String
   - initiatedAt: DateTime
   - initiatedBy: UUID
   - repository: String
   - techStack: List[String]

2. RequirementAdded
   - projectId: UUID
   - requirementId: UUID
   - title: String
   - description: String
   - priority: String
   - addedAt: DateTime
   - addedBy: UUID
   - dependencies: List[UUID]

3. TaskCreated
   - projectId: UUID
   - taskId: UUID
   - requirementId: UUID
   - title: String
   - description: String
   - estimatedComplexity: String
   - createdAt: DateTime
   - createdBy: UUID
   - assignedTo: UUID

4. CodeChangeProposed
   - projectId: UUID
   - taskId: UUID
   - changeId: UUID
   - files: List[String]
   - description: String
   - proposedAt: DateTime
   - proposedBy: UUID
   - diff: String
   - reasoning: String

5. CodeChangeReviewed
   - projectId: UUID
   - changeId: UUID
   - reviewerId: UUID
   - reviewedAt: DateTime
   - status: String
   - comments: List[Dict]
   - suggestedChanges: Dict

6. CodeChangeImplemented
   - projectId: UUID
   - changeId: UUID
   - implementedAt: DateTime
   - implementedBy: UUID
   - finalDiff: String
   - affectedFiles: List[String]

7. TestResultRecorded
   - projectId: UUID
   - testId: UUID
   - changeId: UUID
   - result: String
   - coverage: Float
   - recordedAt: DateTime
   - failures: List[Dict]

## Commands
1. InitiateProject
   - name: String
   - description: String
   - repository: String
   - techStack: List[String]

2. AddRequirement
   - projectId: UUID
   - title: String
   - description: String
   - priority: String
   - dependencies: List[UUID]

3. CreateTask
   - projectId: UUID
   - requirementId: UUID
   - title: String
   - description: String
   - estimatedComplexity: String
   - assignedTo: UUID

4. ProposeCodeChange
   - projectId: UUID
   - taskId: UUID
   - files: List[String]
   - description: String
   - diff: String
   - reasoning: String

5. ReviewCodeChange
   - projectId: UUID
   - changeId: UUID
   - status: String
   - comments: List[Dict]
   - suggestedChanges: Dict

6. ImplementCodeChange
   - projectId: UUID
   - changeId: UUID
   - finalDiff: String
   - affectedFiles: List[String]

## Views/Projections
1. ProjectOverviewView
   - projectId: UUID
   - name: String
   - description: String
   - status: String
   - progress: Float
   - activeRequirements: Integer
   - completedRequirements: Integer
   - activeTasks: Integer
   - completedTasks: Integer

2. RequirementsView
   - projectId: UUID
   - requirements: List[Requirement]
     - id: UUID
     - title: String
     - status: String
     - tasks: List[Task]
     - dependencies: List[UUID]
     - progress: Float

3. TaskBoardView
   - projectId: UUID
   - columns: Dict[String, List[Task]]
     - backlog: List[Task]
     - inProgress: List[Task]
     - review: List[Task]
     - done: List[Task]

4. CodeChangeView
   - projectId: UUID
   - pendingChanges: List[Change]
   - implementedChanges: List[Change]
   - changesByFile: Dict[String, List[Change]]

## Workflows
1. Start New Project
   ```
   Command: InitiateProject
   Event: ProjectInitiated
   Views:
   - Create ProjectOverviewView
   ```

2. Add Project Requirement
   ```
   Command: AddRequirement
   Event: RequirementAdded
   Views:
   - Update ProjectOverviewView
   - Update RequirementsView
   ```

3. Create and Assign Task
   ```
   Command: CreateTask
   Event: TaskCreated
   Views:
   - Update RequirementsView
   - Update TaskBoardView
   - Update ProjectOverviewView
   ```

4. Propose and Review Code Change
   ```
   Command: ProposeCodeChange
   Event: CodeChangeProposed
   Command: ReviewCodeChange
   Event: CodeChangeReviewed
   Command: ImplementCodeChange
   Event: CodeChangeImplemented
   Views:
   - Update CodeChangeView
   - Update TaskBoardView
   ```

## Agent Roles and Responsibilities
1. Project Manager Agent
   - Breaks down requirements into tasks
   - Assigns priorities
   - Monitors progress
   - Identifies bottlenecks

2. Developer Agent
   - Analyzes tasks
   - Proposes code changes
   - Implements approved changes
   - Writes tests

3. Reviewer Agent
   - Reviews code changes
   - Suggests improvements
   - Ensures code quality
   - Validates against requirements

4. Testing Agent
   - Runs test suites
   - Reports coverage
   - Identifies regressions
   - Suggests test improvements

## Business Rules
1. Each code change must be linked to a task
2. Tasks must be linked to requirements
3. Code changes require review before implementation
4. All implemented changes must pass tests
5. Requirements can't be marked complete until all tasks are done
6. Dependencies between requirements must be respected
7. Code changes must include reasoning and documentation

## Special Considerations
1. Concurrent Development
   - Multiple agents can work on different tasks
   - Changes must be coordinated
   - Conflicts must be detected and resolved

2. Quality Assurance
   - Automated testing
   - Code review standards
   - Coverage requirements
   - Performance benchmarks

3. Progress Tracking
   - Real-time updates
   - Bottleneck detection
   - Resource allocation
   - Timeline predictions 