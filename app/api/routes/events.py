"""Event extraction API endpoints"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.api.dependencies import get_task_storage, get_llm_client, get_current_user, get_redis_client
from app.storage import TaskStorage
from app.analyzer.llm_client import LLMClient
from app.analyzer.event_extractor import EventExtractor, DomainEvent, EventType
from app.storage.redis_client import RedisClient


router = APIRouter(prefix="/api/events", tags=["events"])


class EventResponse(BaseModel):
    """Response model for domain events"""
    name: str
    event_type: str
    description: str
    actor: str | None = None
    affected_entity: str | None = None
    triggers: List[str] = []
    source_task_id: str
    metadata: Dict[str, Any] = {}


class EventCatalogResponse(BaseModel):
    """Complete event catalog for a task tree"""
    task_id: str
    total_events: int
    events_by_type: Dict[str, int]
    events: List[EventResponse]


@router.post("/extract/{task_id}", response_model=EventCatalogResponse)
async def extract_events(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    llm_client: LLMClient = Depends(get_llm_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Extract domain events from a task and its entire subtask tree.

    This analyzes all atomic tasks in the tree and identifies:
    - User actions
    - System events
    - External integrations
    - State changes
    """
    # Get the root task
    root_task = await storage.get_task(task_id)
    if not root_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify ownership
    if root_task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get entire task tree
    task_tree = await storage.get_task_tree(task_id)

    # Extract events
    extractor = EventExtractor(llm_client)
    events = await extractor.extract_events(task_tree)

    # Count events by type
    events_by_type = {}
    for event in events:
        event_type = event.event_type.value
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

    # Convert to response format
    event_responses = [
        EventResponse(
            name=e.name,
            event_type=e.event_type.value,
            description=e.description,
            actor=e.actor,
            affected_entity=e.affected_entity,
            triggers=e.triggers,
            source_task_id=e.source_task_id,
            metadata=e.metadata
        )
        for e in events
    ]

    return EventCatalogResponse(
        task_id=task_id,
        total_events=len(events),
        events_by_type=events_by_type,
        events=event_responses
    )


@router.get("/{task_id}", response_model=EventCatalogResponse)
async def get_cached_events(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(get_current_user)
):
    """
    Get previously extracted events from cache.

    If no cached events exist, returns empty catalog.
    Use POST /extract/{task_id} to generate events.
    """
    # Get the root task
    root_task = await storage.get_task(task_id)
    if not root_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify ownership
    if root_task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Try to get cached events from task metadata
    cached_events = root_task.metadata.get("extracted_events", [])

    if not cached_events:
        return EventCatalogResponse(
            task_id=task_id,
            total_events=0,
            events_by_type={},
            events=[]
        )

    # Count by type
    events_by_type = {}
    for event in cached_events:
        event_type = event["event_type"]
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

    # Convert to response format
    event_responses = [EventResponse(**e) for e in cached_events]

    return EventCatalogResponse(
        task_id=task_id,
        total_events=len(cached_events),
        events_by_type=events_by_type,
        events=event_responses
    )


async def _generate_event_model_task(
    task_id: str,
    user_id: str,
    storage: TaskStorage,
    llm_client: LLMClient,
    redis_client: RedisClient
):
    """Background task to generate event model and emit WebSocket events."""
    from app.analyzer.context_aware_domain_analyzer import ContextAwareDomainAnalyzer
    from app.services.context_engine_client import ContextEngineClient
    from app.websocket.events import TaskEventEmitter

    # Create event emitter for WebSocket notifications
    task_event_emitter = TaskEventEmitter()

    try:
        # Get the root task
        root_task = await storage.get_task(task_id)
        if not root_task:
            print(f"[EventModel] Task {task_id} not found")
            return

        # Emit started event
        await task_event_emitter.emit_event_modeling_started(root_task, user_id)

        # Get entire task tree
        task_tree = await storage.get_task_tree(task_id)
        if not task_tree:
            await task_event_emitter.emit_event_modeling_error(
                root_task, "Task tree not found", user_id
            )
            return

        # Get all tasks except root from the TaskTree object
        all_tasks = [task for task in task_tree.tasks.values() if task.depth > 0]

        if not all_tasks:
            await task_event_emitter.emit_event_modeling_error(
                root_task, "No subtasks found to analyze", user_id
            )
            return

        # Create analyzers
        context_engine_client = ContextEngineClient(redis_client=redis_client)

        unified_analyzer = ContextAwareDomainAnalyzer(
            llm_client,
            context_engine_client,
            task_event_emitter
        )

        # Analyze domain
        print(f"[EventModel] Generating event model for task {task_id} with {len(all_tasks)} subtasks")
        event_model_analysis = await unified_analyzer.analyze_domain(
            all_tasks,
            root_task,
            user_id,
            project_id=task_id
        )

        # Store event model in task metadata
        if not isinstance(root_task.metadata, dict):
            root_task.metadata = {}

        # Store events
        if event_model_analysis.get("events"):
            root_task.metadata["extracted_events"] = [
                {
                    "name": e.name,
                    "event_type": e.event_type.value,
                    "description": e.description,
                    "actor": e.actor,
                    "affected_entity": e.affected_entity,
                    "triggers": e.triggers,
                    "source_task_id": e.source_task_id,
                    "metadata": e.metadata,
                    "payload": e.metadata.get("payload", []) if isinstance(e.metadata, dict) else []
                }
                for e in event_model_analysis["events"]
            ]

        # Store commands, read models, etc.
        for key in ["commands", "read_models", "user_interactions", "automations", "swimlanes", "chapters", "wireframes", "data_flow", "slices"]:
            if event_model_analysis.get(key):
                root_task.metadata[key] = event_model_analysis[key]

        # Save updated task
        await storage.save_task(root_task)

        # Emit completed event
        await task_event_emitter.emit_event_modeling_completed(
            root_task,
            user_id,
            events_count=len(event_model_analysis.get("events", [])),
            commands_count=len(event_model_analysis.get("commands", [])),
            read_models_count=len(event_model_analysis.get("read_models", [])),
            interactions_count=len(event_model_analysis.get("user_interactions", [])),
            automations_count=len(event_model_analysis.get("automations", [])),
            chapters_count=len(event_model_analysis.get("chapters", [])),
            swimlanes_count=len(event_model_analysis.get("swimlanes", []))
        )

        print(f"[EventModel] Completed event model for task {task_id}")

    except Exception as e:
        print(f"[EventModel] Error generating event model for task {task_id}: {e}")
        import traceback
        traceback.print_exc()

        # Try to emit error event
        try:
            root_task = await storage.get_task(task_id)
            if root_task:
                await task_event_emitter.emit_event_modeling_error(
                    root_task, str(e), user_id
                )
        except Exception as emit_error:
            print(f"[EventModel] Failed to emit error event: {emit_error}")


@router.post("/generate-model/{task_id}")
async def generate_event_model(
    task_id: str,
    background_tasks: BackgroundTasks,
    storage: TaskStorage = Depends(get_task_storage),
    llm_client: LLMClient = Depends(get_llm_client),
    redis_client: RedisClient = Depends(get_redis_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a complete event model for an existing task.

    This starts background processing and returns immediately.
    Progress and completion are sent via WebSocket events:
    - event_modeling.started
    - event_modeling.progress
    - event_modeling.completed
    - event_modeling.error
    """
    # Get the root task to validate it exists and user has access
    root_task = await storage.get_task(task_id)
    if not root_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify ownership
    if root_task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get entire task tree to validate
    task_tree = await storage.get_task_tree(task_id)
    if not task_tree:
        raise HTTPException(status_code=400, detail="Task tree not found")

    # Get all tasks except root from the TaskTree object
    all_tasks = [task for task in task_tree.tasks.values() if task.depth > 0]

    if not all_tasks:
        raise HTTPException(status_code=400, detail="No subtasks found to analyze")

    # Add background task - it will emit WebSocket events for progress
    background_tasks.add_task(
        _generate_event_model_task,
        task_id,
        current_user["id"],
        storage,
        llm_client,
        redis_client
    )

    return {
        "message": "Event model generation started",
        "task_id": task_id,
        "status": "processing",
        "subtasks_count": len(all_tasks)
    }
