"""Project context API endpoints - proxies to Contex"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_task_storage, get_current_user
from app.storage import TaskStorage
from app.services.context_engine_client import ContextEngineClient

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def get_context_engine() -> ContextEngineClient:
    """Get Context Engine client instance"""
    client = ContextEngineClient()
    if not await client.health_check():
        raise HTTPException(
            status_code=503,
            detail="Context Engine is not available"
        )
    return client


@router.get("/{project_id}/context")
async def get_project_context(
    project_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all context data for a project.

    This proxies to Contex's /projects/{project_id}/data endpoint
    and returns all published data for the project.

    The project_id is the root task_id.
    """
    # Verify the task exists and user has access
    task = await storage.get_task(project_id)
    if not task:
        raise HTTPException(status_code=404, detail="Project not found")

    if task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get context from Contex
    try:
        context_engine = ContextEngineClient()
        project_data = await context_engine.get_project_data(project_id)
    except Exception as e:
        print(f"[Projects] Failed to fetch context from Contex: {e}")
        # Return empty context if Contex is unavailable rather than failing
        project_data = None

    # Build response with task status info
    response = {
        "project_id": project_id,
        "task_status": task.status.value,
        "task_description": task.description,
        "is_processing": task.status.value in ["pending", "processing"],
        "context": project_data or {},
        "metadata": task.metadata or {}
    }

    # Add summary stats if we have context data
    if project_data:
        response["stats"] = _compute_stats(project_data)

    return response


def _compute_stats(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute summary statistics from context data"""
    stats = {}

    # Count tasks
    if "decomposed_tasks" in context_data:
        tasks_data = context_data["decomposed_tasks"]
        if isinstance(tasks_data, dict):
            stats["total_tasks"] = tasks_data.get("total_tasks", 0)
            stats["max_depth"] = tasks_data.get("max_depth", 0)

    # Count epics and stories
    if "epics_and_stories" in context_data:
        epics_data = context_data["epics_and_stories"]
        if isinstance(epics_data, dict):
            stats["total_epics"] = epics_data.get("total_epics", 0)
            stats["total_stories"] = epics_data.get("total_stories", 0)

    # Count events and commands from event model
    if "event_model" in context_data:
        event_model = context_data["event_model"]
        if isinstance(event_model, dict):
            stats["total_events"] = len(event_model.get("events", []))
            stats["total_commands"] = len(event_model.get("commands", []))
            stats["total_read_models"] = len(event_model.get("read_models", []))

    # Tech stack info
    if "tech_stack" in context_data:
        tech_stack = context_data["tech_stack"]
        if isinstance(tech_stack, dict):
            stats["has_tech_stack"] = True
            # Extract key technologies
            techs = []
            for category, value in tech_stack.items():
                if isinstance(value, str):
                    techs.append(value)
                elif isinstance(value, dict):
                    techs.extend(value.keys())
            stats["technologies"] = techs[:5]  # Top 5

    return stats
