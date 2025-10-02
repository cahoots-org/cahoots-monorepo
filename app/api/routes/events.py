"""Event extraction API endpoints"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_task_storage, get_llm_client, get_current_user
from app.storage import TaskStorage
from app.analyzer.llm_client import LLMClient
from app.analyzer.event_extractor import EventExtractor, DomainEvent, EventType


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
