# Resumable Code Generation

## Problem

Currently, code generation is a monolithic operation. If it fails at any point (scaffold, task 15/20, integration), the only option is to start over. This wastes:
- Time (re-running already-completed work)
- LLM tokens (re-generating code that already exists)
- User patience

## Insight

The system is already built on **immutable, event-sourced foundations**:

1. **Git** - Complete code history, every task's commits are preserved
2. **Contex** - Event-sourced semantic index with time travel
3. **Redis** - Generation state tracking what completed/failed/blocked
4. **Task decomposition** - Immutable task tree with dependencies

This means we can **reconcile** the actual state of the world (git) with the desired state (task list) and resume from any point.

## Design

### Core Principle: Reconciliation by Default

Instead of separate "start", "retry", and "resume" endpoints, we have **one endpoint** that always reconciles state before proceeding:

```
POST /api/codegen/projects/{id}/generate
{
  "tech_stack": "nodejs-api",
  "force": false  // default: reconcile and resume from current state
                  // true: wipe everything and start fresh
}
```

**Default behavior (`force: false`):**
1. Check if repo exists → skip scaffold if yes
2. Check which tasks are merged to main → skip those
3. Continue from where we left off

**Force mode (`force: true`):**
1. Delete existing repo or create fresh
2. Start from scratch

### State Reconciliation

Instead of trusting in-memory state, we **derive** the current state by examining git:

```
Actual State (Git)          Desired State (Tasks)
─────────────────           ──────────────────────
✓ scaffold exists           Task 1: Create user auth
✓ task/abc merged           Task 2: Add login endpoint
✓ task/def merged           Task 3: Add logout endpoint
✗ task/ghi NOT merged       Task 4: Add password reset
                            Task 5: Add email verification
```

The reconciliation tells us: "Resume from Task 4"

### Enhanced Status Endpoint

The existing status endpoint includes reconciliation info:

```
GET /api/codegen/projects/{id}/generate/status
```

Response:
```json
{
  "project_id": "abc-123",
  "status": "failed",
  "tech_stack": "nodejs-api",
  "repo_url": "http://gitea:3000/cahoots/abc-123.git",

  "progress_percent": 75.0,
  "total_tasks": 20,
  "completed_tasks": 15,
  "failed_tasks": 2,
  "blocked_tasks": 3,

  "last_error": "Merge conflict in task-16",

  "can_resume": true,
  "resume_from": "generating",
  "tasks_to_retry": ["task-16", "task-17"]
}
```

### Simplified API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/projects/{id}/generate` | POST | Start or resume generation (reconciles by default) |
| `/projects/{id}/generate/status` | GET | Get status with resume info |
| `/projects/{id}/generate/cancel` | POST | Cancel in-progress generation |

**Removed:**
- `/generate/retry` - replaced by default reconciliation behavior
- `/generate/resume` - replaced by default reconciliation behavior
- `/generate/reconcile` - info included in status endpoint

### Implementation

#### 1. Git State Discovery

Add method to discover what's been merged to main:

```python
async def get_merged_task_ids(
    gitea: GiteaClient,
    owner: str,
    repo: str
) -> Set[str]:
    """
    Get task IDs that have been merged to main.

    Examines commit history for task branch merge patterns.
    """
    try:
        commits = await gitea.list_commits(owner, repo, branch="main", limit=500)
    except Exception:
        return set()  # Repo doesn't exist or is empty

    merged_tasks = set()
    for commit in commits:
        message = commit.get("commit", {}).get("message", "")
        # Match patterns like "task/abc123" or "Merge branch 'task/abc123'"
        for match in re.finditer(r"task/([a-f0-9-]+)", message):
            merged_tasks.add(match.group(1))

    return merged_tasks
```

#### 2. Scaffold Detection

```python
async def check_scaffold_exists(
    gitea: GiteaClient,
    owner: str,
    repo: str
) -> bool:
    """Check if project scaffold exists in repo."""
    try:
        # Check for key scaffold files
        contents = await gitea.get_directory_contents(owner, repo, "", ref="main")
        file_names = {f["name"] for f in contents}

        # Look for typical scaffold indicators
        scaffold_markers = {"package.json", "pyproject.toml", "go.mod", "Cargo.toml"}
        return bool(file_names & scaffold_markers)
    except Exception:
        return False
```

#### 3. Reconciliation Logic

```python
@dataclass
class ReconciliationResult:
    """Result of reconciling Git state with desired state."""
    repo_exists: bool
    scaffold_complete: bool
    completed_task_ids: Set[str]
    pending_task_ids: List[str]  # Ordered by dependency
    failed_task_ids: Set[str]
    can_resume: bool
    resume_from: str  # "scaffold", "generating", "integration"


class GenerationReconciler:
    """Reconciles Redis state with Git reality."""

    def __init__(self, gitea: GiteaClient, state_store: GenerationStateStore):
        self.gitea = gitea
        self.state_store = state_store

    async def reconcile(
        self,
        project_id: str,
        tasks: List[Dict],
        owner: str = "cahoots-bot"
    ) -> ReconciliationResult:
        """
        Reconcile actual Git state with desired task state.

        Returns what's actually done vs what needs to be done.
        """
        task_ids = {t["id"] for t in tasks}

        # Check repo existence
        try:
            await self.gitea.get_repository(owner, project_id)
            repo_exists = True
        except Exception:
            repo_exists = False

        if not repo_exists:
            return ReconciliationResult(
                repo_exists=False,
                scaffold_complete=False,
                completed_task_ids=set(),
                pending_task_ids=[t["id"] for t in tasks],
                failed_task_ids=set(),
                can_resume=True,
                resume_from="scaffold"
            )

        # Check scaffold
        scaffold_complete = await check_scaffold_exists(self.gitea, owner, project_id)

        # Check which tasks are actually merged
        merged_task_ids = await get_merged_task_ids(self.gitea, owner, project_id)
        completed = merged_task_ids & task_ids

        # Build dependency graph to determine pending tasks
        graph = TaskDependencyGraph.from_tasks(tasks)

        # Get pending tasks (dependencies met, not completed)
        pending = []
        for task in tasks:
            task_id = task["id"]
            if task_id in completed:
                continue
            # Check dependencies
            node = graph.get_task(task_id)
            deps_met = all(d in completed for d in (node.depends_on or []))
            if deps_met:
                pending.append(task_id)

        # Load Redis state to find explicitly failed tasks
        state = await self.state_store.load(project_id)
        failed = set(state.failed_tasks.keys()) if state else set()
        # Only count as failed if not already completed in git
        failed = failed - completed

        # Determine resume point
        if not scaffold_complete:
            resume_from = "scaffold"
        elif pending or failed:
            resume_from = "generating"
        else:
            resume_from = "integration"

        return ReconciliationResult(
            repo_exists=True,
            scaffold_complete=scaffold_complete,
            completed_task_ids=completed,
            pending_task_ids=pending,
            failed_task_ids=failed,
            can_resume=True,
            resume_from=resume_from
        )
```

#### 4. Updated Generate Endpoint

```python
@router.post("/projects/{project_id}/generate")
async def start_generation(
    project_id: str,
    request: StartGenerationRequest,
    background_tasks: BackgroundTasks,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> GenerationStatusResponse:
    """
    Start or resume code generation for a project.

    By default, reconciles current state and resumes from where it left off.
    Use force=true to start fresh.
    """
    # ... auth checks ...

    # Get tasks
    tasks = await get_project_tasks(project_id, storage)
    if not tasks:
        raise HTTPException(status_code=400, detail="No tasks found")

    # Force mode: start fresh
    if request.force:
        # Delete existing repo if present
        try:
            await gitea.delete_repository("cahoots-bot", project_id)
        except Exception:
            pass

        skip_scaffold = False
        skip_task_ids = set()
        start_phase = "scaffold"
    else:
        # Reconcile mode: figure out where we are
        reconciler = GenerationReconciler(gitea, state_store)
        result = await reconciler.reconcile(project_id, tasks)

        skip_scaffold = result.scaffold_complete
        skip_task_ids = result.completed_task_ids
        start_phase = result.resume_from

    # Initialize or update state
    state = GenerationState(
        project_id=project_id,
        status=GenerationStatus.PENDING,
        tech_stack=request.tech_stack,
        repo_url=f"http://gitea:3000/cahoots-bot/{project_id}.git",
        total_tasks=len(tasks),
        completed_tasks=list(skip_task_ids),
    )
    await state_store.save(state)

    # Start background task
    background_tasks.add_task(
        run_generation_task,
        project_id=project_id,
        user_id=current_user["id"],
        config=GenerationConfig(tech_stack=request.tech_stack),
        tasks=tasks,
        repo_url=state.repo_url,
        state_store=state_store,
        # Resume parameters
        skip_scaffold=skip_scaffold,
        skip_task_ids=skip_task_ids,
        start_phase=start_phase,
    )

    return _state_to_response(state)
```

#### 5. Updated Status Endpoint

```python
@router.get("/projects/{project_id}/generate/status")
async def get_generation_status(
    project_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> GenerationStatusResponse:
    """
    Get generation status with resume information.
    """
    # ... auth checks ...

    state = await state_store.load(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="No generation found")

    # Add reconciliation info if generation is failed/complete
    can_resume = False
    resume_from = None
    tasks_to_retry = []

    if state.status in (GenerationStatus.FAILED, GenerationStatus.COMPLETE):
        tasks = await get_project_tasks(project_id, storage)
        if tasks:
            reconciler = GenerationReconciler(gitea, state_store)
            result = await reconciler.reconcile(project_id, tasks)

            can_resume = bool(result.pending_task_ids or result.failed_task_ids)
            resume_from = result.resume_from
            tasks_to_retry = list(result.pending_task_ids) + list(result.failed_task_ids)

    return GenerationStatusResponse(
        # ... existing fields ...
        can_resume=can_resume,
        resume_from=resume_from,
        tasks_to_retry=tasks_to_retry[:10],  # Limit for response size
    )
```

#### 6. Updated CodeGenerator

```python
class CodeGenerator:
    async def generate(
        self,
        project_id: str,
        tasks: List[Dict],
        repo_url: str,
        tech_stack_info: Optional[Dict] = None,
        # Resume parameters
        skip_scaffold: bool = False,
        skip_task_ids: Optional[Set[str]] = None,
        start_phase: str = "scaffold",
    ) -> GenerationState:
        """
        Run code generation, with support for resumption.
        """
        skip_task_ids = skip_task_ids or set()

        # Initialize metrics
        self.metrics = MetricsCollector(project_id, self.config.tech_stack)
        self.metrics.record_project_start(source="api")

        try:
            state = await self.state_store.load(project_id)
            state.start()
            await self._save_and_emit(state, "generation_started", {
                "resumed": start_phase != "scaffold" or bool(skip_task_ids),
                "skipped_tasks": len(skip_task_ids),
            })

            # Build graph from ALL tasks (need full graph for dependencies)
            graph = TaskDependencyGraph.from_tasks(tasks)
            state.total_tasks = len(tasks)

            # Phase 1: Scaffold (skip if resuming past it)
            if start_phase == "scaffold" and not skip_scaffold:
                await self._create_repository(state, project_id)
                await self._run_scaffold(state, tasks, tech_stack_info)

            # Phase 2: Task generation
            if start_phase in ("scaffold", "generating"):
                state.start_generating()
                await self._save_and_emit(state, "generation_phase_started", {
                    "skipping": len(skip_task_ids),
                })

                # Process tasks, skipping already-completed ones
                await self._process_tasks(state, graph, tasks, skip_task_ids)

            # Check if we can proceed
            if state.status == GenerationStatus.FAILED:
                return state

            # Phase 3: Integration
            if start_phase in ("scaffold", "generating", "integration"):
                state.start_integrating()
                await self._save_and_emit(state, "integration_started")
                await self._run_integration(state, graph)

            # Complete
            if state.status != GenerationStatus.FAILED:
                state.complete()
                await self._save_and_emit(state, "generation_complete")
                self.metrics.record_completion(status="success")

        except Exception as e:
            logger.exception(f"Generation failed for {project_id}")
            state.fail(str(e))
            await self._save_and_emit(state, "generation_error", {"error": str(e)})
            self.metrics.record_completion(status="failed")

        return state

    async def _process_tasks(
        self,
        state: GenerationState,
        graph: TaskDependencyGraph,
        tasks: List[Dict],
        skip_task_ids: Set[str],
    ) -> None:
        """Process tasks, skipping already-completed ones."""
        # Mark skipped tasks as completed in state
        for task_id in skip_task_ids:
            if task_id not in state.completed_tasks:
                state.completed_tasks.append(task_id)

        # Update progress
        await self._save_and_emit(state, "tasks_skipped", {
            "count": len(skip_task_ids),
            "progress": state.progress_percent,
        })

        # Continue with existing _process_tasks logic...
        # The get_ready_tasks() will naturally skip completed tasks
        completed = set(skip_task_ids)
        # ... rest of existing implementation ...
```

### Request/Response Models

```python
class StartGenerationRequest(BaseModel):
    """Request to start code generation."""
    tech_stack: str = Field(..., description="Tech stack to use")
    repo_name: Optional[str] = Field(None, description="Custom repo name")
    force: bool = Field(False, description="Force fresh start, ignoring existing progress")


class GenerationStatusResponse(BaseModel):
    """Response with generation status."""
    project_id: str
    status: str
    tech_stack: str
    repo_url: str
    progress_percent: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    blocked_tasks: int
    current_tasks: List[str]
    started_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]
    last_error: Optional[str]

    # Resume information
    can_resume: bool = False
    resume_from: Optional[str] = None  # "scaffold", "generating", "integration"
    tasks_to_retry: List[str] = []
```

### Benefits

1. **Simpler API**: One endpoint handles start, retry, and resume
2. **Resilient**: API crash? Just call generate again - it resumes automatically
3. **Efficient**: Never re-run completed work unless explicitly forced
4. **Transparent**: Status endpoint shows exactly what will happen on resume
5. **Backward Compatible**: Default behavior is smarter, but API shape unchanged

### Future Enhancements

1. **Contex Time Travel**: Reconstruct semantic state at any checkpoint
2. **Partial Scaffold Resume**: Detect which scaffold files exist
3. **Branch Cleanup**: Clean up orphaned task branches
4. **Selective Retry**: `POST /generate` with `retry_task_ids: ["task-5"]`
