"""Epic and Story management API endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models import Epic, UserStory, StoryStatus, EpicStatus
from app.api.dependencies import get_task_storage, get_task_processor
from app.storage import TaskStorage
from app.processor import TaskProcessor


router = APIRouter(prefix="/api/epics", tags=["epics"])


@router.get("/{epic_id}")
async def get_epic(
    epic_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get an epic by ID."""
    epic = await storage.get_epic(epic_id)
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")

    return {"data": epic.to_dict()}


@router.get("/{epic_id}/stories")
async def get_epic_stories(
    epic_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get all stories for an epic."""
    epic = await storage.get_epic(epic_id)
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")

    stories = await storage.get_stories_for_epic(epic_id)

    return {
        "data": {
            "epic": epic.to_dict(),
            "stories": [story.to_dict() for story in stories],
            "total_stories": len(stories),
            "completed_stories": sum(1 for s in stories if s.status == StoryStatus.COMPLETED),
            "coverage_percentage": epic.calculate_completion_percentage()
        }
    }


@router.get("/task/{root_task_id}")
async def get_task_epics(
    root_task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get all epics for a root task."""
    # Verify the task exists
    task = await storage.get_task(root_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    epics = await storage.get_epics_for_root_task(root_task_id)

    # Calculate aggregate statistics
    total_stories = 0
    completed_stories = 0

    for epic in epics:
        stories = await storage.get_stories_for_epic(epic.id)
        total_stories += len(stories)
        completed_stories += sum(1 for s in stories if s.status == StoryStatus.COMPLETED)

    return {
        "data": {
            "root_task_id": root_task_id,
            "epics": [epic.to_dict() for epic in epics],
            "total_epics": len(epics),
            "total_stories": total_stories,
            "completed_stories": completed_stories,
            "overall_completion": (completed_stories / max(total_stories, 1)) * 100
        }
    }


@router.get("/story/{story_id}")
async def get_story(
    story_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get a story by ID."""
    story = await storage.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return {"data": story.to_dict()}


@router.get("/story/{story_id}/tasks")
async def get_story_tasks(
    story_id: str,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Get all tasks implementing a story."""
    story = await storage.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Get all tasks for this story
    tasks = []
    if story.task_ids:
        task_list = await storage.get_tasks(story.task_ids)
        tasks = [t for t in task_list if t is not None]

    return {
        "data": {
            "story": story.to_dict(),
            "tasks": [task.to_redis_dict() for task in tasks],
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.status == "completed"),
            "completion_percentage": story.calculate_completion_percentage()
        }
    }


@router.patch("/story/{story_id}/status")
async def update_story_status(
    story_id: str,
    status: StoryStatus,
    storage: TaskStorage = Depends(get_task_storage)
) -> dict:
    """Update a story's status."""
    story = await storage.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Update status
    old_status = story.status
    story.status = status
    story.updated_at = datetime.now(timezone.utc)

    # Save updated story
    success = await storage.save_story(story)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update story")

    # If story is now completed, update the epic
    if status == StoryStatus.COMPLETED and old_status != StoryStatus.COMPLETED:
        epic = await storage.get_epic(story.epic_id)
        if epic:
            epic.completed_story_count += 1
            await storage.save_epic(epic)

    return {"data": story.to_dict()}


@router.get("/coverage/{root_task_id}")
async def get_coverage_report(
    root_task_id: str,
    storage: TaskStorage = Depends(get_task_storage),
    processor: TaskProcessor = Depends(get_task_processor)
) -> dict:
    """Get a coverage report for the entire task tree."""
    # Get the task tree
    tree = await storage.get_task_tree(root_task_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Task tree not found")

    # Get epics and stories
    epics = await storage.get_epics_for_root_task(root_task_id)

    all_stories = []
    for epic in epics:
        stories = await storage.get_stories_for_epic(epic.id)
        all_stories.extend(stories)

    # Generate coverage report
    if processor.epic_story_processor:
        report = await processor.epic_story_processor.validate_coverage(
            tree.root,
            tree
        )

        return {
            "data": {
                "root_task_id": root_task_id,
                "is_complete": report.is_complete,
                "coverage_score": report.coverage_score,
                "gaps": [
                    {
                        "level": gap.level,
                        "parent_id": gap.parent_id,
                        "description": gap.description,
                        "severity": gap.severity,
                        "suggested_action": gap.suggested_action
                    } for gap in report.gaps
                ],
                "overlaps": [
                    {
                        "level": overlap.level,
                        "item1_id": overlap.item1_id,
                        "item2_id": overlap.item2_id,
                        "description": overlap.overlap_description,
                        "severity": overlap.severity
                    } for overlap in report.overlaps
                ],
                "statistics": report.statistics,
                "recommendations": report.recommendations
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Epic/Story processor not available")


@router.get("/uncovered")
async def get_uncovered_stories(
    epic_id: Optional[str] = Query(None, description="Filter by specific epic"),
    storage: TaskStorage = Depends(get_task_storage),
    processor: TaskProcessor = Depends(get_task_processor)
) -> dict:
    """Get stories that haven't been fully covered by tasks."""
    if not processor.epic_story_processor:
        raise HTTPException(status_code=500, detail="Epic/Story processor not available")

    uncovered = await processor.epic_story_processor.get_uncovered_stories(epic_id)

    return {
        "data": {
            "uncovered_stories": [story.to_dict() for story in uncovered],
            "total": len(uncovered),
            "filtered_by_epic": epic_id is not None
        }
    }