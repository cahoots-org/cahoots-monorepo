"""Task management API endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models import (
    Task, TaskStatus, TaskRequest, TaskResponse,
    TaskTreeNode, TaskTreeResponse, TaskListResponse, TaskStats
)
from app.api.dependencies import get_task_storage, get_task_processor
from app.storage import TaskStorage
from app.processor import TaskProcessor
from app.websocket.events import task_event_emitter
# from app.auth.dependencies import get_current_user  # TODO: Re-enable auth


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/stats")
async def get_task_stats(
    top_level_only: bool = Query(True),
    storage: TaskStorage = Depends(get_task_storage)
) -> Dict[str, Any]:
    """Get task statistics."""
    # Get task counts by status
    task_counts = await storage.count_tasks_by_status()

    return {
        "total": sum(task_counts.values()),
        "completed": task_counts.get(TaskStatus.COMPLETED, 0),
        "in_progress": task_counts.get(TaskStatus.IN_PROGRESS, 0),
        "pending": task_counts.get(TaskStatus.SUBMITTED, 0),
        "rejected": task_counts.get(TaskStatus.REJECTED, 0),
        "awaiting_approval": task_counts.get(TaskStatus.AWAITING_APPROVAL, 0)
    }


@router.post("")
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    processor: TaskProcessor = Depends(get_task_processor),
    storage: TaskStorage = Depends(get_task_storage)
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
        if request.tech_preferences:
            context["tech_stack"] = request.tech_preferences.model_dump()
        if request.repository:
            context["repository"] = request.repository.model_dump()

        # Add human review flag if requested
        if request.requires_approval:
            context["require_human_review"] = True

        # Create the root task immediately
        root_task = Task(
            id=str(uuid.uuid4()),
            description=request.description,
            status=TaskStatus.PROCESSING,
            depth=0,
            user_id=request.user_id,
            context=context
        )

        # Save the root task so it's immediately visible
        await storage.save_task(root_task)

        # Emit task created event immediately
        await task_event_emitter.emit_task_created(root_task, request.user_id)

        # Process the task decomposition in the background
        background_tasks.add_task(
            processor.process_task_async,
            root_task,
            context,
            request.user_id,
            request.max_depth
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
    user_id: Optional[str] = None,
    top_level_only: bool = Query(False),
    storage: TaskStorage = Depends(get_task_storage)
) -> TaskListResponse:
    """List tasks with optional filtering."""
    # Get tasks based on filters
    if status:
        tasks = await storage.get_tasks_by_status(status)
    elif user_id:
        tasks = await storage.get_user_tasks(
            user_id,
            limit=page_size,
            offset=(page - 1) * page_size
        )
    else:
        # Get all tasks (simplified for now, should paginate)
        all_keys = await storage.redis.keys(f"{storage.task_prefix}*")
        task_ids = [key.replace(storage.task_prefix, "") for key in all_keys]
        all_tasks = await storage.get_tasks(task_ids)
        tasks = [t for t in all_tasks if t is not None]

    # Filter for root-level tasks only if requested
    if top_level_only:
        tasks = [t for t in tasks if t.parent_id is None]

    # Sort tasks by created_at date (newest first)
    tasks.sort(key=lambda t: t.created_at, reverse=True)

    # Apply pagination after filtering and sorting
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_tasks = tasks[start_idx:end_idx]

    # Calculate stats (use all filtered tasks for accurate stats)
    task_counts = await storage.count_tasks_by_status()

    # If filtering for top-level only, calculate total from filtered list
    if top_level_only:
        total = len(tasks)  # Total root-level tasks
    else:
        total = sum(task_counts.values())

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

    # Convert tasks to responses with recursive subtask counting for root tasks
    task_responses = []
    for task in paginated_tasks:
        task_response = TaskResponse.from_task(task)
        # For root tasks, count all descendants recursively
        if task.parent_id is None:
            descendant_count = await storage.count_all_descendants(task.id)
            task_response.children_count = descendant_count
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