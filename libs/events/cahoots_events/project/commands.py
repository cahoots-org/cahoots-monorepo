"""Project management domain commands"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..base import Command


@dataclass
class CreateProject(Command):
    """Command to create a new project"""
    name: str
    description: str
    repository: str
    tech_stack: List[str]
    created_by: UUID


@dataclass
class UpdateProjectStatus(Command):
    """Command to update project status"""
    project_id: UUID
    status: str
    reason: str
    updated_by: UUID


@dataclass
class SetProjectTimeline(Command):
    """Command to set project timeline"""
    project_id: UUID
    start_date: datetime
    target_date: datetime
    milestones: List[Dict]
    set_by: UUID


@dataclass
class AddRequirement(Command):
    """Command to add a requirement"""
    project_id: UUID
    title: str
    description: str
    priority: str
    dependencies: List[UUID]
    added_by: UUID


@dataclass
class CompleteRequirement(Command):
    """Command to complete a requirement"""
    project_id: UUID
    requirement_id: UUID
    completed_by: UUID


@dataclass
class BlockRequirement(Command):
    """Command to block a requirement"""
    project_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID


@dataclass
class UnblockRequirement(Command):
    """Command to unblock a requirement"""
    project_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID


@dataclass
class ChangeRequirementPriority(Command):
    """Command to change requirement priority"""
    project_id: UUID
    requirement_id: UUID
    new_priority: str
    reason: str
    changed_by: UUID


@dataclass
class CreateTask(Command):
    """Command to create a task"""
    project_id: UUID
    requirement_id: UUID
    title: str
    description: str
    complexity: str
    created_by: UUID


@dataclass
class CompleteTask(Command):
    """Command to complete a task"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    completed_by: UUID


@dataclass
class AssignTask(Command):
    """Command to assign a task"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    assignee_id: UUID
    assigned_by: UUID


@dataclass
class BlockTask(Command):
    """Command to block a task"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID


@dataclass
class UnblockTask(Command):
    """Command to unblock a task"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID


@dataclass
class ChangeTaskPriority(Command):
    """Command to change task priority"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    new_priority: str
    reason: str
    changed_by: UUID 