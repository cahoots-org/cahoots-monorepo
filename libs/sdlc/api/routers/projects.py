from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...domain.views import (
    CodeChangeView,
    ProjectOverviewView,
    RequirementsView,
    TaskBoardView,
)

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str
    repository: str
    tech_stack: List[str]


class RequirementCreate(BaseModel):
    title: str
    description: str
    priority: str
    dependencies: List[UUID] = []


class TaskCreate(BaseModel):
    requirement_id: UUID
    title: str
    description: str
    complexity: str


class CodeChangeProposal(BaseModel):
    files: List[str]
    description: str
    reasoning: str


class CodeChangeReview(BaseModel):
    status: str
    comments: str
    suggested_changes: str


@router.post("")
async def create_project(project: ProjectCreate, request: Request):
    """Create a new project"""
    try:
        events = request.state.project_handler.handle_create_project(project)
        return {"message": "Project created", "project_id": events[0].project_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: UUID, request: Request):
    """Get project details"""
    view = request.state.view_store.get_view(project_id, ProjectOverviewView)
    if not view:
        raise HTTPException(status_code=404, detail="Project not found")
    return view


@router.post("/{project_id}/requirements")
async def add_requirement(project_id: UUID, requirement: RequirementCreate, request: Request):
    """Add requirement to project"""
    try:
        events = request.state.project_handler.handle_add_requirement(
            project_id=project_id,
            title=requirement.title,
            description=requirement.description,
            priority=requirement.priority,
            dependencies=requirement.dependencies,
        )
        return {"message": "Requirement added", "requirement_id": events[0].requirement_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/requirements")
async def list_requirements(project_id: UUID, request: Request):
    """List project requirements"""
    view = request.state.view_store.get_view(project_id, RequirementsView)
    if not view:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"requirements": view.requirements}


@router.post("/{project_id}/tasks")
async def create_task(project_id: UUID, task: TaskCreate, request: Request):
    """Create a new task"""
    try:
        events = request.state.project_handler.handle_create_task(
            project_id=project_id,
            requirement_id=task.requirement_id,
            title=task.title,
            description=task.description,
            complexity=task.complexity,
        )
        return {"message": "Task created", "task_id": events[0].task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/tasks")
async def list_tasks(project_id: UUID, request: Request):
    """List project tasks"""
    view = request.state.view_store.get_view(project_id, TaskBoardView)
    if not view:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"tasks": view.columns}


@router.post("/{project_id}/code-changes")
async def propose_code_change(project_id: UUID, proposal: CodeChangeProposal, request: Request):
    """Propose a code change"""
    try:
        events = request.state.project_handler.handle_propose_code_change(
            project_id=project_id,
            files=proposal.files,
            description=proposal.description,
            reasoning=proposal.reasoning,
        )
        return {"message": "Code change proposed", "change_id": events[0].change_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/code-changes/{change_id}/review")
async def review_code_change(
    project_id: UUID, change_id: UUID, review: CodeChangeReview, request: Request
):
    """Review a code change"""
    try:
        events = request.state.project_handler.handle_review_code_change(
            project_id=project_id,
            change_id=change_id,
            status=review.status,
            comments=review.comments,
            suggested_changes=review.suggested_changes,
        )
        return {"message": "Code change reviewed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/code-changes/{change_id}/implement")
async def implement_code_change(project_id: UUID, change_id: UUID, request: Request):
    """Implement a code change"""
    try:
        events = request.state.project_handler.handle_implement_code_change(
            project_id=project_id, change_id=change_id
        )
        return {"message": "Code change implemented"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/code-changes")
async def list_code_changes(project_id: UUID, request: Request):
    """List code changes"""
    view = request.state.view_store.get_view(project_id, CodeChangeView)
    if not view:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "pending_changes": view.pending_changes,
        "implemented_changes": view.implemented_changes,
    }
