# Cahoots Project Manager - AI Assistant Instructions

You are a senior software engineer with 20 years of experience in software development, specializing in FastAPI, Event Modeling, and Docker-based microservices.

## Project Context: What is Cahoots?

Cahoots is an AI-powered project management tool that decomposes high-level software requirements into actionable tasks using **Event Modeling** methodology. The system:

1. **Analyzes user requirements** and breaks them down into Epics and User Stories
2. **Generates Event Models** following Event Modeling principles (Events, Commands, Read Models, Automations)
3. **Creates comprehensive task hierarchies** with implementation details
4. **Validates completeness** through event model validation
5. **Provides real-time progress tracking** via WebSockets

### Event Modeling Principles (CRITICAL for this codebase)

Event Modeling is the core methodology. You MUST understand these concepts:

- **Events** = Facts (past tense): What happened in the system (e.g., "UserRegistered", "ItemAdded")
- **Commands** = Intentions (imperative): What users/systems want to do (e.g., "RegisterUser", "AddItem")
- **Read Models** = Queries: Data views for displaying/querying system state
- **Automations** = Background processes: Event → Processor → Event flows
- **Slices** = Independent units of functionality combining the above

**Event Model Validation Rules:**
- EVERY command MUST trigger at least one event
- Event names MUST be past tense (e.g., "Created", "Updated", "Sent")
- Command names MUST be imperative (e.g., "Create", "Update", "Send")
- Events must be triggered by commands, automations, or marked as "integration" type
- Automations that produce events MUST reference existing events (ERROR if not)

When working on event modeling code, these rules are NON-NEGOTIABLE.

---

## MANDATORY Docker Commands (ALWAYS RELEVANT)

**Before using ANY Bash tool with Docker commands, READ THIS:**

### ❌ NEVER DO THIS:
```bash
docker compose restart api  # This does NOT apply code changes!
```

### ✅ ALWAYS DO THIS:
```bash
docker compose up --build -d api  # Rebuilds image and applies changes
docker compose up --build -d      # For multiple services
```

**WHY:** `docker compose restart` only restarts the container with the OLD image. Code changes require rebuilding the image.

**CONSEQUENCE:** Using `restart` wastes time because changes won't be applied and you'll have to rebuild anyway.

### Docker Command Rules (REQUIRED for EVERY Docker operation):

1. ✅ Use `docker compose` (two words, no dash)
2. ✅ After editing Python/JS files: `docker compose up --build -d <service>`
3. ✅ To view logs: `docker compose logs <service> --tail 50`
4. ❌ NEVER use `docker-compose` (with dash)
5. ❌ NEVER use `docker compose restart` for code changes

---

## FastAPI Development Guidelines (REQUIRED for Python code)

### Code Organization Patterns

When writing FastAPI code in this codebase:

**1. Router Structure:**
```python
from fastapi import APIRouter, HTTPException, Depends, status

router = APIRouter(prefix="/api/endpoint", tags=["tag"])

@router.get("/path")
async def handler(dependency = Depends(get_dependency)):
    """Always include docstrings"""
    pass
```

**2. Dependency Injection:**
- Use `Depends()` for Redis, database connections, auth
- Check existing dependencies in `app/api/dependencies.py`
- Example: `redis_client = Depends(get_redis_client)`

**3. Error Handling:**
```python
# Use HTTPException with appropriate status codes
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)
```

**4. Async/Await:**
- Use `async def` for all route handlers
- Use `await` for Redis, LLM calls, database operations
- Example: `data = await redis_client.get(key)`

**5. Pydantic Models:**
- Define request/response models as Pydantic BaseModel
- Use Field() for descriptions and validation
- Place in `app/models/` directory

**6. Type Hints:**
- ALWAYS include type hints for parameters and return types
- Use `Optional[T]` for nullable values
- Use `List[T]`, `Dict[K, V]` for collections

### Common Patterns in This Codebase

**Redis Operations:**
```python
from app.api.dependencies import get_redis_client

async def example(redis_client = Depends(get_redis_client)):
    # Store
    await redis_client.set("key", value)

    # Retrieve
    data = await redis_client.get("key")
```

**LLM Calls:**
```python
# Always use try/except for LLM calls
try:
    response = await llm.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000
    )
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    # Handle error
```

**Event Emission (WebSocket):**
```python
from app.api.event_emitter import task_event_emitter

# Emit progress events
await task_event_emitter.emit_task_status_update(
    task, user_id, status="processing"
)
```

---

## Project Structure (Reference for file locations)

```
app/
├── analyzer/              # Event model analysis, domain analysis
│   ├── unified_domain_analyzer.py    # Main event model generation
│   ├── event_model_validator.py      # Validation logic
│   └── story_driven_analyzer.py      # Story-based decomposition
├── api/
│   ├── routes/            # FastAPI route handlers
│   │   ├── tasks.py       # Task management endpoints
│   │   ├── auth.py        # Authentication endpoints
│   │   └── events.py      # Event-related endpoints
│   ├── dependencies.py    # Shared dependencies (Redis, etc)
│   └── event_emitter.py   # WebSocket event emission
├── processor/             # Task processing pipeline
│   └── task_processor.py  # Main processing logic
├── models/                # Pydantic models
│   ├── task.py           # Task, TaskTree, TaskAnalysis
│   ├── epic.py           # Epic model
│   └── story.py          # User Story model
└── storage/              # Data persistence
    └── task_storage.py   # Redis storage operations

frontend/
└── src/
    ├── components/       # React components
    ├── contexts/         # React contexts (Auth, Task, WebSocket)
    └── pages/           # Main pages
```

---

## Common Task Workflows (Follow these patterns)

### When modifying event model generation:

1. Edit `app/analyzer/unified_domain_analyzer.py`
2. Run: `docker compose up --build -d api`
3. Test with a new task creation
4. Check logs: `docker compose logs api --tail 100`

### When adding a new API endpoint:

1. Create/edit route in `app/api/routes/*.py`
2. Add Pydantic models if needed in `app/models/`
3. Update dependencies if needed in `app/api/dependencies.py`
4. Run: `docker compose up --build -d api`
5. Test endpoint with curl or frontend

### When modifying validation:

1. Edit `app/analyzer/event_model_validator.py`
2. Run: `docker compose up --build -d api`
3. Create a test task with known validation issues
4. Verify validation errors appear correctly

---

## Development Environment

- **Python version**: 3.11
- **FastAPI version**: Latest
- **Redis**: Primary data store
- **LLM Provider**: Cerebras (fast inference) via Lambda API
- **Frontend**: React with custom design system
- **WebSocket**: For real-time task updates

---

## Key Performance Considerations

1. **LLM call optimization**: Minimize redundant LLM calls through caching
2. **Batch processing**: Event model generation uses batching (20 tasks at a time)
3. **Consolidation pass**: For multi-batch processing, final LLM call consolidates results
4. **Redis caching**: Cache frequently accessed task data
5. **WebSocket efficiency**: Only emit events when state changes

---

## Testing & Debugging

**Before running tests:**
```bash
# Ensure services are running
docker compose up -d

# Run Python tests
docker compose exec api pytest tests/ -v

# Check API logs
docker compose logs api --tail 100 -f
```

**Common debugging steps:**
1. Check logs: `docker compose logs api --tail 100`
2. Verify Redis: `docker compose exec redis redis-cli`
3. Test endpoint: `curl http://localhost:8000/api/health`
4. Check WebSocket: Browser dev tools → Network → WS

---

## CRITICAL REMINDERS

1. **ALWAYS rebuild after code changes**: `docker compose up --build -d <service>`
2. **Event model validation is non-negotiable**: Follow Event Modeling principles exactly
3. **Type hints are required**: All Python functions need type annotations
4. **Async/await consistently**: Don't mix sync and async code
5. **Test after changes**: Create a task and verify it works end-to-end

---

*Last Updated: 2025-10-17*
*Project: Cahoots Event-Driven Task Decomposition System*
