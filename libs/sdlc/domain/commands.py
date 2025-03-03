from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID


@dataclass
class Command:
    """Base class for all commands"""

    command_id: UUID
    correlation_id: UUID  # For tracking related commands/events


@dataclass
class CreateProject(Command):
    name: str
    description: str
    repository: str
    tech_stack: List[str]
    created_by: UUID


@dataclass
class UpdateProjectStatus(Command):
    project_id: UUID
    status: str
    reason: str
    updated_by: UUID


@dataclass
class SetProjectTimeline(Command):
    project_id: UUID
    start_date: datetime
    target_date: datetime
    milestones: List[Dict]
    set_by: UUID


@dataclass
class AddRequirement(Command):
    project_id: UUID
    title: str
    description: str
    priority: str
    dependencies: List[UUID]
    added_by: UUID


@dataclass
class CompleteRequirement(Command):
    project_id: UUID
    requirement_id: UUID
    completed_by: UUID


@dataclass
class BlockRequirement(Command):
    project_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID


@dataclass
class UnblockRequirement(Command):
    project_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID


@dataclass
class ChangeRequirementPriority(Command):
    project_id: UUID
    requirement_id: UUID
    new_priority: str
    reason: str
    changed_by: UUID


@dataclass
class CreateTask(Command):
    project_id: UUID
    requirement_id: UUID
    title: str
    description: str
    complexity: str
    created_by: UUID


@dataclass
class CompleteTask(Command):
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    completed_by: UUID


@dataclass
class AssignTask(Command):
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    assignee_id: UUID
    assigned_by: UUID


@dataclass
class BlockTask(Command):
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID


@dataclass
class UnblockTask(Command):
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID


@dataclass
class ChangeTaskPriority(Command):
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    new_priority: str
    reason: str
    changed_by: UUID


@dataclass
class ProposeCodeChange(Command):
    project_id: UUID
    task_id: UUID
    files: List[str]
    description: str
    diff: str
    reasoning: str
    proposed_by: UUID


@dataclass
class ReviewCodeChange(Command):
    project_id: UUID
    change_id: UUID
    reviewer_id: UUID
    status: str
    comments: List[Dict]
    suggested_changes: Dict


@dataclass
class ImplementCodeChange(Command):
    project_id: UUID
    change_id: UUID
    implemented_by: UUID
    final_diff: str
    affected_files: List[str]
