# Cahoots Code Generation Architecture

## Overview

This document describes Cahoots' code generation system, which transforms **implementation tasks** (from project decomposition) into working, tested code using **Test-Driven Development (TDD)**.

## Core Principles

### 1. Task-Based Generation

Code generation works from **implementation tasks** - clear, actionable units with:
- **Description**: What needs to be built (user-visible)
- **Implementation Details**: How to build it (technical guidance)
- **Dependencies**: Which tasks must complete first

Tasks come from the decomposition phase where epics are broken into stories, and stories into tasks.

### 2. Agents as Autonomous Developers

Agents receive **tools** to interact with the codebase - they explore, read, and write files like a human developer:
- Scales to any project size
- Enables natural pattern discovery
- Simplifies payloads (just the task, not the whole codebase)

### 3. Test-First Generation

For each task:
1. **Generate tests first** based on task description
2. **Generate code** to make those tests pass
3. **Fix loop** if tests fail (max 3 attempts)
4. **Merge to main** when tests pass

---

## System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER COMPOSE                                  │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Cahoots    │  │  Workspace   │  │    Runner    │  │    Gitea     │   │
│  │     API      │  │   Service    │  │   Service    │  │   (Git)      │   │
│  │              │  │              │  │              │  │              │   │
│  │ Orchestrates │  │ File tools   │  │ Runs tests   │  │ Self-hosted  │   │
│  │ generation   │  │ Git commits  │  │ in containers│  │ repositories │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                 │                 │                 │            │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 │            │
│  ┌────────────┐   ┌─────────────────┐                        │            │
│  │  Context   │   │     Redis       │                        │            │
│  │  Engine    │   │  (state/queue)  │                        │            │
│  │ (optional) │   └─────────────────┘                        │            │
│  └────────────┘                                              │            │
│         │                                                     │            │
└─────────┼─────────────────────────────────────────────────────┼────────────┘
          │                                                     │
          ▼                                                     │
    ┌───────────┐                                              │
    │    LLM    │◄─────────────────────────────────────────────┘
    │ (Cerebras)│
    └───────────┘
```

### 1. CodeGenerator (Orchestrator)

Location: `app/codegen/orchestrator/generator.py`

Coordinates the generation pipeline:
- Builds task dependency graph
- Runs ScaffoldAgent to create project structure
- Processes tasks in dependency order (with parallelization)
- Runs IntegrationAgent to wire everything together
- Emits progress events via WebSocket

### 2. Workspace Service

Location: `workspace-service/`

Provides file operation tools to agents:
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Create/overwrite file (auto-commits)
- `edit_file(path, old, new)` - Surgical edit within file
- `list_files(path, pattern)` - List directory contents
- `grep(pattern, path)` - Search for code patterns

Also handles:
- Repository creation in Gitea
- Branch management
- PR creation and merging

### 3. Runner Service

Location: `runner-service/`

Executes tests in isolated containers:
- Clones the repo at specific branch
- Installs dependencies
- Runs test commands
- Returns pass/fail results with error details

### 4. Gitea (Self-Hosted Git)

Lightweight git server for project repositories:
- Unlimited repos at no per-repo cost
- ~512MB RAM footprint
- Full Git API for programmatic control
- Used for all code storage and merging

---

## Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    CODE GENERATION FLOW                          │
│                                                                  │
│  1. Initialize                                                   │
│     └─► Create Gitea repository                                 │
│     └─► Build task dependency graph                             │
│                                                                  │
│  2. Scaffold (ScaffoldAgent)                                    │
│     └─► Create package.json / pyproject.toml                    │
│     └─► Create directory structure (src/, tests/)               │
│     └─► Create test framework config                            │
│     └─► Create Hello World test that passes                     │
│                                                                  │
│  3. Generate Tasks (TaskAgent per task)                         │
│     └─► Process tasks in dependency order                       │
│     └─► Up to 3 tasks in parallel (configurable)                │
│     └─► Each task: tests → code → run → fix → merge             │
│                                                                  │
│  4. Integration (IntegrationAgent)                              │
│     └─► Wire components together                                │
│     └─► Update exports/imports                                  │
│     └─► Final verification                                      │
│                                                                  │
│  5. Complete                                                     │
│     └─► All code merged to main branch                          │
│     └─► Repository ready for deployment                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Structure

Tasks are the unit of code generation:

```json
{
  "id": "task-uuid-here",
  "description": "Create user registration endpoint",
  "implementation_details": "POST /api/users endpoint using Express. Validate email format, hash password with bcrypt, store in users table. Return 201 with user object (no password).",
  "story_points": 3,
  "depends_on": ["task-uuid-for-database-setup"],
  "keywords": ["auth", "users", "registration"]
}
```

### Key Fields

| Field | Purpose |
|-------|---------|
| `description` | User-visible summary of what the task does |
| `implementation_details` | Technical guidance for the LLM |
| `depends_on` | Task IDs that must complete first |
| `story_points` | Complexity estimate (1-8) |
| `keywords` | For semantic file discovery |

---

## Task Dependency Graph

Tasks have natural dependencies based on what they build upon:

```
┌─────────────────────────────────────────────────────────────────┐
│  Task Dependencies                                               │
│                                                                  │
│  Level 0 (No dependencies - can run in parallel):               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Database   │  │   Config    │  │   Logger    │             │
│  │   Setup     │  │   Setup     │  │   Setup     │             │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘             │
│         │                │                                       │
│         ▼                ▼                                       │
│  Level 1 (Depend on L0):                                        │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   User      │  │   Auth      │                              │
│  │   Model     │  │   Setup     │                              │
│  └──────┬──────┘  └──────┬──────┘                              │
│         │                │                                       │
│         ▼                ▼                                       │
│  Level 2 (Depend on L1):                                        │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │ Registration│  │   Login     │                              │
│  │  Endpoint   │  │  Endpoint   │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

### Parallel Processing

- Tasks at the same dependency level run in parallel
- Max 3 concurrent tasks (configurable via `max_parallel_tasks`)
- When a task completes, newly-unblocked tasks dispatch immediately

---

## Agent Architecture

### Agent Types

| Agent | Responsibility | When Used |
|-------|---------------|-----------|
| **ScaffoldAgent** | Creates initial project structure | Once at start |
| **TaskAgent** | Implements a single task via TDD | Once per task |
| **IntegrationAgent** | Wires components together | Once at end |
| **MergeAgent** | Handles branch merging with conflict resolution | After each task |

### TaskAgent Flow

The TaskAgent handles the complete TDD cycle for a single task:

```
┌─────────────────────────────────────────────────────────────────┐
│                      TASK AGENT FLOW                             │
│                                                                  │
│  Input:                                                          │
│  - Task description + implementation_details                    │
│  - Tech stack (nodejs-api, python-api, react-spa, etc.)         │
│  - Related files from Context Engine (optional)                 │
│                                                                  │
│  Phase 1: Generate (LLM loop)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Read existing files to understand patterns           │   │
│  │  2. Write test file based on task description            │   │
│  │  3. Write implementation code                            │   │
│  │  4. Call done() to signal completion                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Phase 2: Test (via Runner Service)                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Run: npm test / pytest / go test                        │   │
│  │  If pass → proceed to merge                              │   │
│  │  If fail → enter fix loop                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Phase 3: Fix Loop (max 3 attempts)                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. LLM receives error details                           │   │
│  │  2. Edits code to fix                                    │   │
│  │  3. Re-run tests                                         │   │
│  │  4. Repeat until pass or max attempts                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Phase 4: Merge (via MergeAgent)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Create PR from task branch to main                   │   │
│  │  2. Handle any merge conflicts                           │   │
│  │  3. Merge PR                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Tools

All agents have access to these workspace tools:

```python
WORKSPACE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file (auto-commits)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace text in an existing file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"}
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "pattern": {"type": "string", "default": "*"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for pattern in files",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Signal task completion",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary of what was accomplished"}
                },
                "required": ["summary"]
            }
        }
    }
]
```

---

## Tech Stacks

Tech stacks define conventions for different project types:

Location: `app/codegen/tech_stacks/`

### Available Stacks

| Stack | Description | Test Command |
|-------|-------------|--------------|
| `nodejs-api` | Node.js REST API with Express | `npm test` |
| `python-api` | Python FastAPI service | `pytest` |
| `react-spa` | React Single Page Application | `npm test` |
| `go-api` | Go REST API | `go test -v ./...` |

### Stack Configuration

Each stack defines:
- `src_dir`: Source directory (e.g., `src/`, `app/`)
- `test_dir`: Test directory (e.g., `tests/`, `__tests__/`)
- `test_command`: How to run tests
- `config_files`: Template configuration files (package.json, etc.)
- `conventions`: Style guide for the LLM

Example (`nodejs-api.yaml`):
```yaml
name: nodejs-api
display_name: Node.js API
description: REST API using Express and Jest
category: backend

src_dir: src
test_dir: tests
test_command: npm test

config_files:
  package.json: |
    {
      "name": "{{project_name}}",
      "scripts": {
        "test": "jest",
        "start": "node src/index.js"
      },
      "dependencies": {
        "express": "^4.18.2"
      },
      "devDependencies": {
        "jest": "^29.7.0"
      }
    }

conventions: |
  - Use ES6+ syntax
  - Export functions from index.js
  - Tests go in tests/ directory
  - Use Jest for testing
  - Follow Express patterns for routes
```

---

## MergeAgent and Conflict Resolution

The MergeAgent handles merging task branches to main:

Location: `app/codegen/agents/merge_agent.py`

### Merge Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      MERGE AGENT FLOW                            │
│                                                                  │
│  1. Create PR                                                    │
│     └─► task/abc123 → main                                      │
│                                                                  │
│  2. Check Mergeable                                              │
│     └─► If clean → merge immediately                            │
│     └─► If conflicts → resolve with LLM                         │
│                                                                  │
│  3. Conflict Resolution (if needed)                             │
│     └─► Rebase task branch onto main                            │
│     └─► LLM resolves conflicts file-by-file                     │
│     └─► Run tests to verify                                      │
│     └─► Force push resolved branch                              │
│                                                                  │
│  4. Merge PR                                                     │
│     └─► Squash merge to main                                    │
│     └─► Delete task branch                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Singleton Pattern

MergeAgent uses a singleton pattern with a semaphore to prevent concurrent merges (which cause race conditions):

```python
_merge_semaphore = asyncio.Semaphore(1)

async def request_merge(...):
    async with _merge_semaphore:
        # Only one merge at a time
        return await self._do_merge(...)
```

---

## State Management

Generation state is tracked in Redis:

Location: `app/codegen/orchestrator/state.py`

```python
@dataclass
class GenerationState:
    project_id: str
    status: GenerationStatus  # PENDING, SCAFFOLDING, GENERATING, INTEGRATING, COMPLETE, FAILED
    tech_stack: str
    repo_url: str

    # Progress tracking
    total_tasks: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    failed_tasks: Dict[str, str] = field(default_factory=dict)
    blocked_tasks: List[str] = field(default_factory=list)
```

### Status Flow

```
PENDING → SCAFFOLDING → GENERATING → INTEGRATING → COMPLETE
                ↓             ↓            ↓
              FAILED       FAILED       FAILED
```

---

## API Endpoints

Location: `app/api/routes/codegen.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/codegen/projects/{id}/generate` | POST | Start code generation |
| `/api/codegen/projects/{id}/generate/status` | GET | Get generation status |
| `/api/codegen/projects/{id}/files` | GET | List generated files |
| `/api/codegen/projects/{id}/files/{path}` | GET | Get file contents |

### Start Generation Request

```json
{
  "tech_stack": "nodejs-api",
  "tasks": [
    {
      "id": "task-1",
      "description": "Set up Express server",
      "implementation_details": "Create src/index.js with Express app listening on port 3000",
      "depends_on": []
    }
  ]
}
```

### Status Response

```json
{
  "project_id": "abc123",
  "status": "generating",
  "progress": 45,
  "total_tasks": 10,
  "completed_tasks": ["task-1", "task-2", "task-3", "task-4"],
  "current_tasks": ["task-5"],
  "failed_tasks": {},
  "blocked_tasks": []
}
```

---

## Performance Considerations

### Current Bottlenecks

1. **Sequential Merges**: MergeAgent uses a semaphore - only one merge at a time
2. **Test Execution**: Each task runs tests in a fresh container
3. **LLM Latency**: Each agent iteration requires an LLM call

### Optimization Opportunities

1. **Batch Merges**: Merge multiple non-conflicting branches together
2. **Warm Containers**: Keep test containers warm between runs
3. **Parallel Fix Attempts**: Run fixes in parallel for independent files
4. **Skip Merge for Independent Tasks**: If no shared files, merge without checking

---

## Error Handling

### Task Failures

- Tasks retry up to 5 times with exponential backoff
- After max retries, task is marked as "blocked"
- Dependent tasks cannot proceed

### Merge Conflicts

- MergeAgent attempts LLM-based resolution
- If resolution fails tests, original conflict is preserved
- Manual intervention required for complex conflicts

### Generation Failure

- If > 50% of tasks blocked, generation fails
- Partial progress is preserved in the repository
- User can retry or manually complete

---

## File Locations

```
app/codegen/
├── orchestrator/
│   ├── generator.py      # Main CodeGenerator class
│   ├── state.py          # GenerationState dataclass
│   └── dependency_graph.py  # Task dependency graph
├── agents/
│   ├── base.py           # AgentTask, AgentResult, base classes
│   ├── scaffold.py       # ScaffoldAgent
│   ├── task_agent.py     # TaskAgent (TDD cycle)
│   ├── merge_agent.py    # MergeAgent (PR merging)
│   ├── integration_agent.py  # IntegrationAgent
│   └── tools.py          # WORKSPACE_TOOLS definition
└── tech_stacks/
    ├── __init__.py       # get_tech_stack() function
    ├── nodejs-api.yaml
    ├── python-api.yaml
    └── react-spa.yaml
```

---

*Last Updated: December 2024*
