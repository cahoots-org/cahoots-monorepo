"""
Code Generation API Routes

Endpoints for managing code generation from event models:
- Start generation with tech stack selection
- Monitor progress
- Cancel/retry failed generations
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_task_storage, get_redis_client

def _is_dev_admin(current_user: Dict) -> bool:
    """Check if user is admin in development environment only."""
    is_dev = os.environ.get("ENVIRONMENT", "development") == "development"
    return is_dev and current_user.get("is_admin", False)
from app.api.routes.auth import get_current_user
from app.storage import TaskStorage
from app.services.context_engine_client import ContextEngineClient
from app.codegen.orchestrator import (
    CodeGenerator,
    GenerationConfig,
    GenerationState,
    GenerationStateStore,
    GenerationStatus,
)
from app.codegen.tech_stacks import list_tech_stacks, get_tech_stack

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/codegen", tags=["codegen"])


# Request/Response Models

class StartGenerationRequest(BaseModel):
    """Request to start code generation."""
    tech_stack: str = Field(..., description="Tech stack to use (e.g., 'nodejs-api', 'python-api')")
    repo_name: Optional[str] = Field(None, description="Custom repository name")
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
    can_retry: bool
    # Resume information
    can_resume: bool = False
    resume_from: Optional[str] = None  # "scaffold", "generating", "integration"
    tasks_to_retry: List[str] = []


class TechStackInfo(BaseModel):
    """Information about a tech stack."""
    name: str
    display_name: str
    description: str
    category: str = "backend"


class TechStackListResponse(BaseModel):
    """Response listing available tech stacks."""
    tech_stacks: List[TechStackInfo]


# Helper functions

async def get_generation_state_store(
    redis_client=Depends(get_redis_client),
) -> GenerationStateStore:
    """Get the generation state store."""
    return GenerationStateStore(redis_client)


async def get_project_tasks(project_id: str, storage: TaskStorage) -> Optional[List[Dict[str, Any]]]:
    """
    Get implementation tasks for a project.

    Tasks are stored in the task tree after analysis. Each task has:
    - id: unique task identifier
    - description: what needs to be done
    - implementation_details: how to implement it
    - depends_on: list of task IDs this depends on
    - story_points: estimated complexity

    Returns:
        List of task dicts, or None if no tasks exist yet.

    Raises:
        Exception: If there's an error extracting tasks (server error, not client error)
    """
    try:
        # Get the full task tree from storage
        # This returns a TaskTree object with root and tasks dict
        tree = await storage.get_task_tree(project_id)
        if not tree:
            logger.info(f"No task tree found for project {project_id}")
            return None

        # Collect all atomic (implementation) tasks from the TaskTree
        tasks = []

        # TaskTree has a `tasks` dict with all tasks indexed by ID
        # Each task has is_atomic, description, implementation_details, etc.
        for task_id, task in tree.tasks.items():
            if task.is_atomic:
                tasks.append({
                    "id": task.id,
                    "description": task.description or "",
                    "implementation_details": task.implementation_details,
                    "depends_on": task.depends_on or [],
                    "story_points": task.story_points,
                    "story_id": getattr(task, "story_id", None),
                    "epic_id": getattr(task, "epic_id", None),
                })

        if not tasks:
            logger.info(f"No atomic tasks found for project {project_id}")
            return None

        logger.info(f"Found {len(tasks)} implementation tasks for project {project_id}")
        return tasks

    except Exception as e:
        # Log and re-raise - this is a server error, not a client error
        logger.exception(f"Error extracting tasks for project {project_id}: {e}")
        raise


async def emit_generation_event(event_type: str, data: Dict[str, Any]) -> None:
    """Emit a WebSocket event for generation progress."""
    # Import here to avoid circular imports
    from app.websocket.events import task_event_emitter

    try:
        # Use the existing event emitter infrastructure
        await task_event_emitter.emit_custom_event(
            event_type=f"codegen:{event_type}",
            data=data,
            user_id=data.get("user_id"),
        )
    except Exception as e:
        logger.error(f"Failed to emit generation event: {e}")


# Background task for running generation
async def run_generation_task(
    project_id: str,
    user_id: str,
    config: GenerationConfig,
    tasks: List[Dict[str, Any]],
    repo_url: str,
    state_store: GenerationStateStore,
    tech_stack_info: Optional[Dict] = None,
    # Resume parameters
    skip_scaffold: bool = False,
    skip_task_ids: Optional[set] = None,
    start_phase: str = "scaffold",
) -> None:
    """Background task that runs the code generation."""
    try:
        async def event_callback(event_type: str, data: Dict) -> None:
            data["user_id"] = user_id
            await emit_generation_event(event_type, data)

        generator = CodeGenerator(
            config=config,
            state_store=state_store,
            event_callback=event_callback,
        )

        await generator.generate(
            project_id=project_id,
            tasks=tasks,
            repo_url=repo_url,
            tech_stack_info=tech_stack_info,
            # Resume parameters
            skip_scaffold=skip_scaffold,
            skip_task_ids=skip_task_ids,
            start_phase=start_phase,
        )
    except Exception as e:
        logger.exception(f"Generation failed for project {project_id}")
        # Try to update state to failed
        try:
            state = await state_store.load(project_id)
            if state:
                state.fail(str(e))
                await state_store.save(state)
        except Exception:
            pass


# API Endpoints

@router.get("/tech-stacks", response_model=TechStackListResponse)
async def list_available_tech_stacks() -> TechStackListResponse:
    """
    List all available tech stacks for code generation.

    Returns information about each supported tech stack including
    name, display name, and description.
    """
    stacks = list_tech_stacks()
    return TechStackListResponse(
        tech_stacks=[TechStackInfo(**stack) for stack in stacks]
    )


@router.get("/tech-stacks/{stack_name}")
async def get_tech_stack_details(stack_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific tech stack.

    Includes file patterns, commands, dependencies, and templates.
    """
    stack = get_tech_stack(stack_name)
    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tech stack '{stack_name}' not found",
        )

    return {
        "name": stack.name,
        "display_name": stack.display_name,
        "description": stack.description,
        "category": stack.category,
        "src_dir": stack.src_dir,
        "test_dir": stack.test_dir,
        "install_command": stack.install_command,
        "test_command": stack.test_command,
        "build_command": stack.build_command,
        "runner_image": stack.runner_image,
    }


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
    Use force=true to start fresh, wiping any existing progress.

    Requires:
    - A valid project with a completed event model
    - Tech stack selection

    The generation runs as a background task. Monitor progress using
    the GET /projects/{project_id}/generate/status endpoint.
    """
    # Verify project exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership (skip for admins in development)
    if not _is_dev_admin(current_user) and task.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Validate tech stack
    tech_stack = get_tech_stack(request.tech_stack)
    if not tech_stack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tech stack: {request.tech_stack}",
        )

    # Check if generation already in progress
    existing_state = await state_store.load(project_id)
    if existing_state and existing_state.status.value in ("pending", "initializing", "generating", "integrating"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Generation already in progress",
        )

    # Get implementation tasks from the project
    tasks = await get_project_tasks(project_id, storage)
    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No implementation tasks found. Complete task decomposition before generating code.",
        )

    # Determine repo URL (from Gitea)
    repo_name = request.repo_name or project_id
    repo_url = f"http://gitea:3000/cahoots-bot/{repo_name}.git"

    # Create generation config
    config = GenerationConfig(
        tech_stack=request.tech_stack,
        max_parallel_tasks=3,
        max_fix_attempts=3,
    )

    # Get tech stack info for scaffolding
    tech_stack_info = None
    if tech_stack:
        tech_stack_info = {
            "name": tech_stack.name,
            "src_dir": tech_stack.src_dir,
            "test_dir": tech_stack.test_dir,
            "runner_image": tech_stack.runner_image,
        }

    # Reconciliation: determine what to skip based on git reality
    skip_scaffold = False
    skip_task_ids = set()
    start_phase = "scaffold"

    if not request.force:
        # Reconcile with git reality via workspace-service
        from app.codegen.orchestrator.reconciler import GenerationReconciler

        try:
            reconciler = GenerationReconciler(
                workspace_url=config.workspace_service_url,
                state_store=state_store,
            )
            result = await reconciler.reconcile(project_id, tasks)

            skip_scaffold = result.scaffold_complete
            skip_task_ids = result.completed_task_ids
            start_phase = result.resume_from

            logger.info(
                f"Reconciliation for {project_id}: "
                f"skip_scaffold={skip_scaffold}, "
                f"skip_tasks={len(skip_task_ids)}, "
                f"start_phase={start_phase}"
            )
        except Exception as e:
            # If reconciliation fails, start fresh
            logger.warning(f"Reconciliation failed for {project_id}, starting fresh: {e}")

    # Initialize state
    state = GenerationState(
        project_id=project_id,
        status=GenerationStatus.PENDING,
        tech_stack=request.tech_stack,
        repo_url=repo_url,
        total_tasks=len(tasks),
        completed_tasks=list(skip_task_ids),
    )
    await state_store.save(state)

    # Start background generation task
    background_tasks.add_task(
        run_generation_task,
        project_id=project_id,
        user_id=current_user["id"],
        config=config,
        tasks=tasks,
        repo_url=repo_url,
        state_store=state_store,
        tech_stack_info=tech_stack_info,
        # Resume parameters
        skip_scaffold=skip_scaffold,
        skip_task_ids=skip_task_ids,
        start_phase=start_phase,
    )

    return _state_to_response(state)


@router.get("/projects/{project_id}/generate/status")
async def get_generation_status(
    project_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> GenerationStatusResponse:
    """
    Get the current status of code generation for a project.

    Returns progress information including:
    - Overall status
    - Task progress
    - Current operations
    - Any errors
    - Resume information (if generation failed/completed)
    """
    # Verify project exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not _is_dev_admin(current_user) and task.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get generation state
    state = await state_store.load(project_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generation in progress for this project",
        )

    # Add reconciliation info if generation is failed/complete
    can_resume = False
    resume_from = None
    tasks_to_retry = []

    if state.status.value in ("failed", "complete", "cancelled"):
        # Get implementation tasks
        tasks = await get_project_tasks(project_id, storage)
        if tasks:
            try:
                from app.codegen.orchestrator.reconciler import GenerationReconciler
                config = GenerationConfig(tech_stack=state.tech_stack)

                reconciler = GenerationReconciler(
                    workspace_url=config.workspace_service_url,
                    state_store=state_store,
                )
                result = await reconciler.reconcile(project_id, tasks)

                can_resume = result.can_resume and result.total_remaining > 0
                resume_from = result.resume_from
                tasks_to_retry = (
                    list(result.pending_task_ids)[:5] +
                    list(result.failed_task_ids)[:5]
                )
            except Exception as e:
                logger.warning(f"Reconciliation failed for status: {e}")

    return _state_to_response(state, can_resume, resume_from, tasks_to_retry)


@router.post("/projects/{project_id}/generate/cancel")
async def cancel_generation(
    project_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Cancel an in-progress code generation.

    Only works if generation is currently running.
    """
    # Verify project exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not _is_dev_admin(current_user) and task.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get generation state
    state = await state_store.load(project_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generation in progress",
        )

    if state.status.value in ("complete", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel generation with status: {state.status.value}",
        )

    state.cancel()
    await state_store.save(state)

    await emit_generation_event("generation_cancelled", {
        "project_id": project_id,
        "user_id": current_user["id"],
    })

    return {"message": "Generation cancelled"}


@router.post("/projects/{project_id}/generate/retry")
async def retry_generation(
    project_id: str,
    background_tasks: BackgroundTasks,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> GenerationStatusResponse:
    """
    Retry a failed code generation.

    Only works if the generation has failed and retries are available.
    """
    # Verify project exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not _is_dev_admin(current_user) and task.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get generation state
    state = await state_store.load(project_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generation found",
        )

    if state.status.value != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed generations",
        )

    if not state.can_retry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No retries remaining. Use 'Keep Trying' to add more retries.",
        )

    # Get implementation tasks
    tasks = await get_project_tasks(project_id, storage)
    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Implementation tasks not found",
        )

    # Create config and restart
    config = GenerationConfig(
        tech_stack=state.tech_stack,
        max_parallel_tasks=3,
        max_fix_attempts=3,
    )

    # Reset state for retry
    state.failed_tasks = {}
    state.blocked_tasks = []
    state.last_error = None
    state.status = GenerationStatus.GENERATING
    await state_store.save(state)

    # Restart generation
    background_tasks.add_task(
        run_generation_task,
        project_id=project_id,
        user_id=current_user["id"],
        config=config,
        tasks=tasks,
        repo_url=state.repo_url,
        state_store=state_store,
    )

    return _state_to_response(state)


@router.post("/projects/{project_id}/generate/keep-trying")
async def add_retries(
    project_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    state_store: GenerationStateStore = Depends(get_generation_state_store),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Add additional retry attempts to a failed generation.

    Adds 3 more retry attempts. Useful when automated fixes didn't work
    but you want to try again.
    """
    # Verify project exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not _is_dev_admin(current_user) and task.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get generation state
    state = await state_store.load(project_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generation found",
        )

    state.add_retries(3)
    await state_store.save(state)

    return {
        "message": "Added 3 retry attempts",
        "can_retry": state.can_retry,
        "total_retries": state.max_retries + state.additional_retries,
    }


def _state_to_response(
    state: GenerationState,
    can_resume: bool = False,
    resume_from: Optional[str] = None,
    tasks_to_retry: Optional[List[str]] = None,
) -> GenerationStatusResponse:
    """Convert GenerationState to response model."""
    return GenerationStatusResponse(
        project_id=state.project_id,
        status=state.status.value if hasattr(state.status, 'value') else state.status,
        tech_stack=state.tech_stack,
        repo_url=state.repo_url,
        progress_percent=state.progress_percent,
        total_tasks=state.total_tasks,
        completed_tasks=len(state.completed_tasks),
        failed_tasks=len(state.failed_tasks),
        blocked_tasks=len(state.blocked_tasks),
        current_tasks=state.current_tasks,
        started_at=state.started_at,
        updated_at=state.updated_at,
        completed_at=state.completed_at,
        last_error=state.last_error,
        can_retry=state.can_retry,
        # Resume information
        can_resume=can_resume,
        resume_from=resume_from,
        tasks_to_retry=tasks_to_retry or [],
    )
