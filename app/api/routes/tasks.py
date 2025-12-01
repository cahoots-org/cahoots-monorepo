"""Task management API endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models import (
    Task, TaskStatus, TaskRequest, TaskResponse,
    TaskTreeNode, TaskTreeResponse, TaskListResponse, TaskStats
)
from app.api.dependencies import get_task_storage, get_task_processor, get_llm_client, get_context_engine_client
from app.api.routes.auth import get_current_user
from app.storage import TaskStorage
from app.processor import TaskProcessor
from app.websocket.events import task_event_emitter
from app.services.tech_stack_decision import TechStackDecisionService
from app.analyzer.llm_client import LLMClient
from app.services.github_context_agent import GitHubContextEnrichmentAgent
from app.config import PromptTuningConfig


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/stats")
async def get_task_stats(
    top_level_only: bool = Query(True),
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get task statistics for the current user."""
    user_id = current_user["id"]
    is_dev_user = user_id == "dev-user-123"

    # Get all tasks for the user
    if is_dev_user:
        # For dev user, get all tasks
        all_tasks = await storage.search_tasks("", limit=10000)
    else:
        # Get user's tasks (returns tuple of tasks, total)
        all_tasks, _ = await storage.get_user_tasks(user_id, limit=10000, offset=0)

    # Filter for root-level tasks only if requested
    if top_level_only:
        all_tasks = [t for t in all_tasks if t.parent_id is None]

    # Count by status
    counts = {
        TaskStatus.COMPLETED: 0,
        TaskStatus.IN_PROGRESS: 0,
        TaskStatus.SUBMITTED: 0,
        TaskStatus.REJECTED: 0,
        TaskStatus.AWAITING_APPROVAL: 0
    }

    for task in all_tasks:
        if task.status in counts:
            counts[task.status] += 1

    return {
        "total": len(all_tasks),
        "completed": counts[TaskStatus.COMPLETED],
        "in_progress": counts[TaskStatus.IN_PROGRESS],
        "pending": counts[TaskStatus.SUBMITTED],
        "rejected": counts[TaskStatus.REJECTED],
        "awaiting_approval": counts[TaskStatus.AWAITING_APPROVAL]
    }


@router.post("")
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    processor: TaskProcessor = Depends(get_task_processor),
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(get_current_user),
    llm_client: LLMClient = Depends(get_llm_client),
    context_engine = Depends(get_context_engine_client)
) -> dict:
    """Create a task and start processing it asynchronously.

    This endpoint:
    1. Creates the root task immediately
    2. Returns the task ID to the frontend
    3. Processes decomposition in the background
    4. Sends WebSocket updates as processing continues
    """
    try:
        # Build context from request
        context = {}

        # Get GitHub token from user's integration
        github_token = None
        user_id = current_user["id"]
        try:
            github_token = await storage.redis.get(f"github_token:{user_id}")
            if github_token:
                github_token = github_token.decode() if isinstance(github_token, bytes) else github_token
                print(f"[TaskAPI] Using GitHub token for user {user_id}")
        except Exception as e:
            print(f"[TaskAPI] Could not fetch GitHub token: {e}")

        # Handle GitHub repo URL if provided
        if request.github_repo_url:
            try:
                print(f"[TaskAPI] Enriching context from GitHub repo: {request.github_repo_url}")

                # Initialize GitHub Context Enrichment Agent
                github_agent = GitHubContextEnrichmentAgent(
                    llm_client=llm_client,
                    github_token=github_token
                )

                # Run context enrichment
                github_context = await github_agent.enrich_task_context(
                    repo_url=request.github_repo_url,
                    user_prompt=request.description,
                    max_iterations=3
                )

                # Add GitHub context to task context
                context["github"] = github_context

                print(f"[TaskAPI] ✓ GitHub context enriched: "
                      f"{github_context['context_metadata']['files_read']} files, "
                      f"confidence: {github_context['context_metadata']['confidence']:.2f}")

                # Detect feature overlap to filter redundant tasks
                try:
                    print(f"[TaskAPI] Detecting feature overlap...")
                    existing_features = await github_agent.detect_feature_overlap(
                        user_prompt=request.description
                    )
                    if existing_features:
                        context["existing_features"] = existing_features
                        print(f"[TaskAPI] ✓ Feature overlap detected: "
                              f"{existing_features['summary']['already_exist']}/{existing_features['summary']['total_requested']} "
                              f"features already exist ({existing_features['summary']['overlap_percentage']:.1f}% overlap)")

                except Exception as e:
                    print(f"[TaskAPI] ⚠ Feature overlap detection failed: {e}")
                    # Continue without feature overlap detection - non-blocking

            except Exception as e:
                print(f"[TaskAPI] ⚠ GitHub context enrichment failed: {e}")
                # Continue without GitHub context - non-blocking
                context["github_error"] = str(e)

        if request.repository:
            context["repository"] = request.repository.model_dump()

        # Determine tech stack using constrained catalog and LLM decision-making
        # This happens BEFORE decomposition to guide all subsequent task generation
        # Strategy:
        # - If GitHub context available: Match the existing repository's tech stack
        # - Otherwise: Use prescribed default stack (Python + FastAPI + React)
        tech_decision_service = TechStackDecisionService(llm_client)
        tech_stack = await tech_decision_service.determine_tech_stack(
            task_description=request.description,
            event_model=None,  # Event model not available yet
            github_context=context.get("github")  # Pass GitHub context if available
        )
        context["tech_stack"] = tech_stack

        print(f"[TaskAPI] Tech stack determined: {tech_stack.get('language')}, "
              f"frontend={tech_stack.get('frontend')}, backend={tech_stack.get('backend')}, "
              f"from_github={context.get('github') is not None}")

        # Add human review flag if requested
        if request.requires_approval:
            context["require_human_review"] = True

        # Parse prompt config if provided
        prompt_config = None
        if request.prompt_config:
            try:
                prompt_config = PromptTuningConfig(**request.prompt_config)
                print(f"[TaskAPI] Using custom prompt config: {request.prompt_config}")
            except Exception as e:
                print(f"[TaskAPI] Warning: Invalid prompt_config provided, using defaults: {e}")
                prompt_config = None

        # Create the root task immediately with current user
        user_id = current_user["id"]
        root_task = Task(
            id=str(uuid.uuid4()),
            description=request.description,
            status=TaskStatus.PROCESSING,
            depth=0,
            user_id=user_id,
            context=context
        )

        # Save the root task so it's immediately visible
        await storage.save_task(root_task)

        # Emit task created event immediately
        await task_event_emitter.emit_task_created(root_task, user_id)

        # Publish context to Context Engine for AI-powered analysis
        if context_engine:
            try:
                # Publish GitHub context if available
                if context.get("github"):
                    await context_engine.publish_github_context(
                        project_id=root_task.id,
                        user_id=user_id,
                        github_context=context["github"]
                    )

                # Publish existing features if available
                if context.get("existing_features"):
                    await context_engine.publish_existing_features(
                        project_id=root_task.id,
                        user_id=user_id,
                        existing_features=context["existing_features"]
                    )

                # Publish tech stack
                if context.get("tech_stack"):
                    await context_engine.publish_data(
                        project_id=root_task.id,
                        data_key="tech_stack",
                        data=context["tech_stack"]
                    )

            except Exception as e:
                print(f"[TaskAPI] ⚠ Failed to interact with Context Engine: {e}")
                import traceback
                traceback.print_exc()
                # Continue without Context Engine - non-blocking

        # Process the task decomposition in the background
        background_tasks.add_task(
            processor.process_task_async,
            root_task,
            context,
            request.user_id,
            request.max_depth,
            prompt_config  # Pass prompt config to processor
        )

        # Return the root task immediately for frontend navigation
        return {"data": TaskResponse.from_task(root_task).dict()}

    except Exception as e:
        print(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get a task by ID."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_response = TaskResponse.from_task(task)
    # For root tasks, count all descendants recursively
    if task.parent_id is None:
        descendant_count = await storage.count_all_descendants(task.id)
        task_response.children_count = descendant_count

    return {"data": task_response.dict()}


@router.get("/{task_id}/tree")
async def get_task_tree(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get the full task tree starting from the given task."""
    tree = await storage.get_task_tree(task_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Task tree not found")

    # Build tree node recursively
    async def build_tree_node(task: Task) -> TaskTreeNode:
        children = await storage.get_children(task.id)
        child_nodes = []
        for child in children:
            child_node = await build_tree_node(child)
            child_nodes.append(child_node)

        return TaskTreeNode.from_task(task, children=child_nodes)

    root_node = await build_tree_node(tree.root)

    # Calculate statistics
    total_tasks = len(tree.tasks)
    completed_tasks = sum(1 for t in tree.tasks.values() if t.status == TaskStatus.COMPLETED)
    atomic_tasks = sum(1 for t in tree.tasks.values() if t.is_atomic)
    max_depth = max(tree.depth_map.keys()) if tree.depth_map else 0
    total_points = sum(t.story_points or 0 for t in tree.tasks.values())
    completion = tree.calculate_completion_percentage()

    # Create the tree response structure that frontend expects
    tree_data = root_node.dict()
    tree_data.update({
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "atomic_tasks": atomic_tasks,
        "max_depth": max_depth,
        "total_story_points": total_points if total_points > 0 else None,
        "completion_percentage": completion
    })

    return {"data": tree_data}


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[TaskStatus] = None,
    top_level_only: bool = Query(False),
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(get_current_user)
) -> TaskListResponse:
    """List tasks with optional filtering and pagination."""
    # Get current user
    user_id = current_user["id"]

    # Calculate offset for pagination
    offset = (page - 1) * page_size

    # Use optimized storage method with filtering and pagination
    paginated_tasks, total = await storage.get_user_tasks(
        user_id=user_id,
        limit=page_size,
        offset=offset,
        top_level_only=top_level_only,
        status=status,
        sort_by_created=True
    )

    # Calculate stats (use cached status counts)
    task_counts = await storage.count_tasks_by_status()

    stats = TaskStats(
        total=total,
        completed=task_counts.get(TaskStatus.COMPLETED, 0),
        in_progress=task_counts.get(TaskStatus.IN_PROGRESS, 0),
        rejected=task_counts.get(TaskStatus.REJECTED, 0),
        pending=task_counts.get(TaskStatus.SUBMITTED, 0),
        atomic=sum(1 for t in paginated_tasks if t.is_atomic),
        average_complexity=sum(t.complexity_score for t in paginated_tasks) / len(paginated_tasks) if paginated_tasks else 0,
        average_depth=sum(t.depth for t in paginated_tasks) / len(paginated_tasks) if paginated_tasks else 0
    )

    # Convert tasks to responses
    # For root tasks, use subtasks length instead of recursive count for performance
    task_responses = []
    for task in paginated_tasks:
        task_response = TaskResponse.from_task(task)
        # Use direct subtasks count (immediate children only)
        # This avoids N recursive queries and is sufficient for UI
        if task.parent_id is None:
            task_response.children_count = len(task.subtasks) if task.subtasks else 0
        task_responses.append(task_response)

    return TaskListResponse(
        tasks=task_responses,
        total=total,
        page=page,
        page_size=page_size,
        stats=stats
    )


@router.put("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: TaskStatus,
    storage: TaskStorage = Depends(get_task_storage)
) -> TaskResponse:
    """Update task status."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update status
    success = await storage.update_task(task_id, {"status": status})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update task")

    # Get updated task
    task = await storage.get_task(task_id)
    return TaskResponse.from_task(task)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    updates: Dict[str, Any],
    storage: TaskStorage = Depends(get_task_storage)
) -> TaskResponse:
    """Update task with arbitrary fields."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task
    success = await storage.update_task(task_id, updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update task")

    # Get updated task
    task = await storage.get_task(task_id)
    return TaskResponse.from_task(task)


@router.patch("/{task_id}/event-model")
async def update_event_model(
    task_id: str,
    updates: Dict[str, Any],
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Update event model markdown for a task and re-validate."""
    from app.analyzer.event_model_validator import EventModelValidator

    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Extract the event_model_markdown from the request
    event_model_markdown = updates.get("event_model_markdown")
    if event_model_markdown is None:
        raise HTTPException(status_code=400, detail="event_model_markdown is required")

    # Update the task's metadata
    if task.metadata is None:
        task.metadata = {}

    task.metadata["event_model_markdown"] = event_model_markdown

    # Re-validate the existing event model structure if it exists
    # Note: We validate the structured data (events, commands, etc.), not the markdown
    # The markdown is just a representation - the structured data is the source of truth
    if all(key in task.metadata for key in ['extracted_events', 'commands', 'read_models']):
        validator = EventModelValidator()
        analysis = {
            'events': task.metadata.get('extracted_events', []),
            'commands': task.metadata.get('commands', []),
            'read_models': task.metadata.get('read_models', []),
            'user_interactions': task.metadata.get('user_interactions', []),
            'automations': task.metadata.get('automations', [])
        }

        is_valid, issues = validator.validate(analysis)
        validation_summary = validator.get_validation_summary()

        # Store validation results
        task.metadata["event_model_validation"] = {
            "is_valid": is_valid,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "details": issue.details
                }
                for issue in issues
            ],
            "summary": validation_summary
        }

    # Save the updated task
    success = await storage.update_task(task_id, {"metadata": task.metadata})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update event model")

    # Get updated task
    task = await storage.get_task(task_id)
    return {"data": TaskResponse.from_task(task).dict()}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> TaskResponse:
    """Mark task as completed."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status
    # Update status to completed
    success = await storage.update_task(task_id, {"status": TaskStatus.COMPLETED})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to complete task")

    # Get updated task and emit event
    task = await storage.get_task(task_id)
    await task_event_emitter.emit_task_status_changed(task, old_status, task.user_id)

    return TaskResponse.from_task(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> Dict[str, str]:
    """Delete a task and all its children."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all descendants
    tree = await storage.get_task_tree(task_id)
    deleted_count = 1
    if tree:
        deleted_count = len(tree.tasks)
        # Delete all tasks in tree
        for tid in tree.tasks.keys():
            await storage.delete_task(tid)

    # Emit deletion event
    await task_event_emitter.emit_task_deleted(task, task.user_id, deleted_count)

    return {"message": f"Deleted task {task_id} and {deleted_count - 1} children"}


@router.get("/{task_id}/children", response_model=List[TaskResponse])
async def get_children(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> List[TaskResponse]:
    """Get immediate children of a task."""
    children = await storage.get_children(task_id)
    return [TaskResponse.from_task(child) for child in children]


@router.post("/search", response_model=List[TaskResponse])
async def search_tasks(
    query: str,
    limit: int = Query(50, ge=1, le=100),
    storage: TaskStorage = Depends(get_task_storage)
) -> List[TaskResponse]:
    """Search tasks by description."""
    tasks = await storage.search_tasks(query, limit)
    return [TaskResponse.from_task(task) for task in tasks]



@router.post("/{task_id}/restart-decomposition")
async def restart_decomposition(
    task_id: str,
    restart_data: Dict[str, Any],
    storage: TaskStorage = Depends(get_task_storage),
    processor: TaskProcessor = Depends(get_task_processor)
) -> TaskResponse:
    """Restart decomposition for a task."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Clear existing subtasks
        task.subtasks = []
        task.status = TaskStatus.PROCESSING
        await storage.save_task(task)

        # Reprocess the task
        tree = await processor.process_task_complete(
            description=task.description,
            context=task.context,
            user_id=task.user_id,
            max_depth=restart_data.get("max_depth", 5)
        )

        return TaskResponse.from_task(tree.root)

    except Exception as e:
        print(f"Error restarting decomposition: {e}")
        task.status = TaskStatus.ERROR
        await storage.save_task(task)
        raise HTTPException(status_code=500, detail=str(e))


async def _reprocess_task(
    task_id: str,
    storage: TaskStorage,
    processor: TaskProcessor
):
    """Background task to reprocess a task."""
    try:
        task = await storage.get_task(task_id)
        if not task:
            print(f"[Reprocess] Task {task_id} not found")
            return

        print(f"[Reprocess] Starting reprocess for task {task_id}")

        # Delete existing subtasks
        tree = await storage.get_task_tree(task_id)
        if tree:
            for tid in list(tree.tasks.keys()):
                if tid != task_id:  # Don't delete root task
                    await storage.delete_task(tid)

        # Clear subtask references and reset status
        task.subtasks = []
        task.status = TaskStatus.PROCESSING

        # Clear event model metadata for regeneration
        if isinstance(task.metadata, dict):
            for key in ['extracted_events', 'commands', 'read_models', 'chapters', 'slices', 'swimlanes']:
                task.metadata.pop(key, None)

        await storage.save_task(task)

        # Reprocess the task
        await processor.process_task_complete(
            description=task.description,
            context=task.context,
            user_id=task.user_id,
            max_depth=task.metadata.get('max_depth', 5) if isinstance(task.metadata, dict) else 5
        )

        print(f"[Reprocess] Completed reprocess for task {task_id}")

    except Exception as e:
        print(f"[Reprocess] Error reprocessing task {task_id}: {e}")
        import traceback
        traceback.print_exc()

        # Mark task as error
        try:
            task = await storage.get_task(task_id)
            if task:
                task.status = TaskStatus.ERROR
                await storage.save_task(task)
        except Exception:
            pass


@router.post("/{task_id}/reprocess")
async def reprocess_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    storage: TaskStorage = Depends(get_task_storage),
    processor: TaskProcessor = Depends(get_task_processor),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reprocess a task from scratch.

    Deletes all subtasks and regenerates the entire project plan.
    Returns immediately; progress sent via WebSocket.
    """
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify ownership
    if task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Add background task
    background_tasks.add_task(
        _reprocess_task,
        task_id,
        storage,
        processor
    )

    return {
        "message": "Reprocessing started",
        "task_id": task_id,
        "status": "processing"
    }


@router.delete("/{task_id}/subtask")
async def delete_subtask(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> Dict[str, str]:
    """Delete a subtask (same as delete task but with different endpoint name)."""
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get parent task and update its subtasks list
    if task.parent_id:
        parent = await storage.get_task(task.parent_id)
        if parent and task_id in parent.subtasks:
            parent.subtasks.remove(task_id)
            await storage.save_task(parent)

    # Delete the task and its children
    tree = await storage.get_task_tree(task_id)
    if tree:
        for task_to_delete_id in tree.tasks.keys():
            await storage.delete_task(task_to_delete_id)
    else:
        await storage.delete_task(task_id)

    return {"message": f"Deleted subtask {task_id}"}


@router.post("/{task_id}/slices")
async def add_slice(
    task_id: str,
    slice_data: Dict[str, Any],
    storage: TaskStorage = Depends(get_task_storage),
    llm_client: LLMClient = Depends(get_llm_client)
) -> dict:
    """Add a new slice to a task's event model with LLM analysis.

    The LLM will:
    - Fill in missing fields (command, events, read model, etc.)
    - Generate GWT scenarios
    - Create wireframe components
    - Ensure consistency with the existing event model
    - Make updates to related slices if needed
    """
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.metadata:
        raise HTTPException(status_code=400, detail="Task has no event model")

    # Extract current event model
    current_event_model = {
        "events": task.metadata.get("extracted_events", []),
        "commands": task.metadata.get("commands", []),
        "read_models": task.metadata.get("read_models", []),
        "automations": task.metadata.get("automations", []),
        "chapters": task.metadata.get("chapters", []),
        "swimlanes": task.metadata.get("swimlanes", []),
        "wireframes": task.metadata.get("wireframes", []),
        "data_flow": task.metadata.get("data_flow", [])
    }

    # Build LLM prompt for slice analysis
    import json
    prompt = f"""You are enhancing an Event Model by adding a new slice.

EXISTING EVENT MODEL:
{json.dumps(current_event_model, indent=2)}

NEW SLICE REQUEST:
Name: {slice_data.get('name')}
Type: {slice_data.get('type')}
Description: {slice_data.get('description', '')}
Chapter: {slice_data.get('chapter')}
Command: {slice_data.get('command', '')}
Read Model: {slice_data.get('read_model', '')}

YOUR TASK:
Analyze the new slice request and the existing event model, then:

1. Fill in missing details for the new slice
2. Generate appropriate events (past tense names)
3. Create GWT scenarios (at least 2: happy path + error case)
4. Generate wireframe components if applicable
5. Add data flow mappings
6. Ensure consistency with existing event model
7. Update related slices/chapters if needed

RULES:
- Event names MUST be past tense (e.g., ItemAdded, CartSubmitted)
- Command names MUST be imperative (e.g., AddItem, SubmitCart)
- State change slices need: command, events, GWT scenarios with given/when/then
- State view slices need: read_model, source_events, GWT scenarios with given/then
- Every slice MUST have at least 2 GWT scenarios
- Wireframes should have simple components (input, button, text, list, etc.)
- Assign slice to appropriate swimlane based on domain

Return JSON with this structure:
{{
  "slice": {{
    "type": "state_change" | "state_view" | "automation",
    "command": "CommandName" (if state_change),
    "read_model": "ReadModelName" (if state_view),
    "events": ["EventName1", "EventName2"],
    "source_events": ["SourceEvent1"] (if state_view),
    "gwt_scenarios": [
      {{"given": "...", "when": "...", "then": "..."}},
      {{"given": "...", "when": "...", "then": "..."}}
    ]
  }},
  "new_command": {{
    "name": "CommandName",
    "description": "...",
    "swimlane": "SwimlaneN ame",
    "triggers_events": ["EventName"],
    "parameters": ["param1", "param2"]
  }} (if needed),
  "new_events": [
    {{
      "name": "EventName",
      "event_type": "user_action" | "system_event" | "integration",
      "description": "...",
      "actor": "User" | "System",
      "affected_entity": "Entity",
      "swimlane": "SwimlaneName",
      "triggered_by": "CommandName" | "AutomationName"
    }}
  ],
  "new_read_model": {{
    "name": "ReadModelName",
    "description": "...",
    "swimlane": "SwimlaneName",
    "data_source": ["EventName1", "EventName2"],
    "fields": ["field1", "field2"]
  }} (if needed),
  "wireframe": {{
    "name": "Screen Name",
    "slice": "{slice_data.get('name')}",
    "type": "state_change" | "state_view",
    "components": [
      {{
        "type": "input" | "button" | "text" | "list",
        "field": "fieldName",
        "label": "Label",
        "triggers": "CommandName" (if button),
        "displays": ["field1"] (if display component)
      }}
    ]
  }},
  "data_flow": [
    {{
      "from": "UI:ScreenName.field",
      "to": "Command:CommandName.field",
      "description": "..."
    }}
  ],
  "chapter_updates": {{
    "chapter_name": "{slice_data.get('chapter')}",
    "add_slice": {{...slice details...}}
  }}
}}

Return ONLY valid JSON, no explanation."""

    try:
        # Call LLM
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
            temperature=0.3
        )

        # Extract JSON from response
        import re
        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            raise HTTPException(status_code=500, detail="Unexpected LLM response format")

        # Parse JSON
        data = None
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            # Try extracting from code block
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
            if code_block_match:
                data = json.loads(code_block_match.group(1))
            else:
                # Try brace matching
                start_idx = content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    in_string = False
                    escape = False

                    for i in range(start_idx, len(content)):
                        char = content[i]

                        if escape:
                            escape = False
                            continue

                        if char == '\\':
                            escape = True
                            continue

                        if char == '"' and not escape:
                            in_string = not in_string
                            continue

                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = content[start_idx:i+1]
                                    data = json.loads(json_str)
                                    break

        if not data:
            raise HTTPException(status_code=500, detail="Failed to parse LLM response")

        # Update event model with new slice data
        metadata = task.metadata

        # Add new command if provided
        if "new_command" in data and data["new_command"]:
            if "commands" not in metadata:
                metadata["commands"] = []
            metadata["commands"].append(data["new_command"])

        # Add new events if provided
        if "new_events" in data and data["new_events"]:
            if "extracted_events" not in metadata:
                metadata["extracted_events"] = []
            metadata["extracted_events"].extend(data["new_events"])

        # Add new read model if provided
        if "new_read_model" in data and data["new_read_model"]:
            if "read_models" not in metadata:
                metadata["read_models"] = []
            metadata["read_models"].append(data["new_read_model"])

        # Add wireframe if provided
        if "wireframe" in data and data["wireframe"]:
            if "wireframes" not in metadata:
                metadata["wireframes"] = []
            metadata["wireframes"].append(data["wireframe"])

        # Add data flow if provided
        if "data_flow" in data and data["data_flow"]:
            if "data_flow" not in metadata:
                metadata["data_flow"] = []
            metadata["data_flow"].extend(data["data_flow"])

        # Update chapter with new slice
        if "chapter_updates" in data and data["chapter_updates"]:
            chapter_name = data["chapter_updates"]["chapter_name"]
            new_slice = data["chapter_updates"]["add_slice"]

            if "chapters" not in metadata:
                metadata["chapters"] = []

            # Find the chapter
            chapter_found = False
            for chapter in metadata["chapters"]:
                if chapter["name"] == chapter_name:
                    if "slices" not in chapter:
                        chapter["slices"] = []
                    chapter["slices"].append(new_slice)
                    chapter_found = True
                    break

            # If chapter not found, create it
            if not chapter_found:
                metadata["chapters"].append({
                    "name": chapter_name,
                    "description": f"Chapter containing {slice_data.get('name')}",
                    "slices": [new_slice]
                })

        # Save updated task
        success = await storage.update_task(task_id, {"metadata": metadata})
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update task")

        # Get updated task
        task = await storage.get_task(task_id)

        return {
            "data": TaskResponse.from_task(task).dict(),
            "analysis": data
        }

    except Exception as e:
        print(f"Error adding slice: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


