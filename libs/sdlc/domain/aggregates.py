from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from .events import (
    ProjectCreated, ProjectStatusUpdated, ProjectTimelineSet,
    RequirementAdded, RequirementCompleted, RequirementPriorityChanged,
    RequirementBlocked, RequirementUnblocked,
    TaskCreated, TaskCompleted, TaskAssigned, TaskPriorityChanged,
    TaskBlocked, TaskUnblocked
)


@dataclass
class Project:
    """Aggregate root for projects"""
    project_id: UUID
    name: str = ''
    description: str = ''
    repository: str = ''
    tech_stack: List[str] = field(default_factory=list)
    status: str = 'planning'  # planning, in_progress, on_hold, completed
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    milestones: List[Dict] = field(default_factory=list)
    requirements: Dict[UUID, 'Requirement'] = field(default_factory=dict)
    active_requirements: int = 0
    completed_requirements: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0

    def apply_event(self, event):
        """Apply an event to update the aggregate state"""
        if isinstance(event, ProjectCreated):
            self.name = event.name
            self.description = event.description
            self.repository = event.repository
            self.tech_stack = event.tech_stack

        elif isinstance(event, ProjectStatusUpdated):
            self.status = event.status

        elif isinstance(event, ProjectTimelineSet):
            self.start_date = event.start_date
            self.target_date = event.target_date
            self.milestones = event.milestones

        elif isinstance(event, RequirementAdded):
            requirement = Requirement(
                requirement_id=event.requirement_id,
                project_id=self.project_id
            )
            requirement.apply_event(event)
            self.requirements[event.requirement_id] = requirement
            self.active_requirements += 1

        elif isinstance(event, RequirementCompleted):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id].apply_event(event)
                self.active_requirements -= 1
                self.completed_requirements += 1

        elif isinstance(event, TaskCreated):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id].apply_event(event)
                self.active_tasks += 1

        elif isinstance(event, TaskCompleted):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id].apply_event(event)
                self.active_tasks -= 1
                self.completed_tasks += 1

        # Forward other events to requirements
        elif any(isinstance(event, evt_type) for evt_type in [
            RequirementPriorityChanged, RequirementBlocked, RequirementUnblocked,
            TaskAssigned, TaskPriorityChanged, TaskBlocked, TaskUnblocked
        ]):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id].apply_event(event)

    def can_complete_requirement(self, requirement_id: UUID) -> bool:
        """Check if a requirement can be completed"""
        if requirement_id not in self.requirements:
            return False
        return self.requirements[requirement_id].can_complete()

    def can_change_status(self, new_status: str) -> bool:
        """Check if project status can be changed"""
        valid_statuses = {'planning', 'in_progress', 'on_hold', 'completed'}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")

        # Can't transition to the same status
        if new_status == self.status:
            return False

        # Validate status transitions
        if new_status == 'completed':
            # Can complete if there are no active requirements
            if self.active_requirements > 0:
                raise ValueError("Cannot complete project with active requirements")
            return True
        elif new_status == 'in_progress':
            # Can start if in planning or coming back from hold
            if self.status not in {'planning', 'on_hold'}:
                raise ValueError("Can only start projects that are in planning or on hold")
            return True
        elif new_status == 'on_hold':
            # Can only put in-progress projects on hold
            if self.status != 'in_progress':
                raise ValueError("Can only put in-progress projects on hold")
            return True
        elif new_status == 'planning':
            # Can return to planning only from in_progress
            if self.status != 'in_progress':
                raise ValueError("Can only return to planning from in-progress status")
            return True

        return True


@dataclass
class Requirement:
    """Aggregate for requirements"""
    requirement_id: UUID
    project_id: UUID
    title: str = ''
    description: str = ''
    priority: str = ''
    status: str = 'active'  # active, blocked, completed
    dependencies: List[UUID] = field(default_factory=list)
    tasks: Dict[UUID, 'Task'] = field(default_factory=dict)
    blocker_description: Optional[str] = None

    def apply_event(self, event):
        """Apply an event to update the aggregate state"""
        if isinstance(event, RequirementAdded):
            self.title = event.title
            self.description = event.description
            self.priority = event.priority
            self.dependencies = event.dependencies

        elif isinstance(event, RequirementCompleted):
            self.status = 'completed'

        elif isinstance(event, RequirementPriorityChanged):
            self.priority = event.new_priority

        elif isinstance(event, RequirementBlocked):
            self.status = 'blocked'
            self.blocker_description = event.blocker_description

        elif isinstance(event, RequirementUnblocked):
            self.status = 'active'
            self.blocker_description = None

        elif isinstance(event, TaskCreated):
            task = Task(
                task_id=event.task_id,
                requirement_id=self.requirement_id,
                project_id=self.project_id
            )
            task.apply_event(event)
            self.tasks[event.task_id] = task

        elif isinstance(event, TaskCompleted):
            if event.task_id in self.tasks:
                self.tasks[event.task_id].apply_event(event)

        elif isinstance(event, TaskAssigned):
            if event.task_id in self.tasks:
                self.tasks[event.task_id].apply_event(event)

        elif isinstance(event, TaskPriorityChanged):
            if event.task_id in self.tasks:
                self.tasks[event.task_id].apply_event(event)

        elif isinstance(event, TaskBlocked):
            if event.task_id in self.tasks:
                self.tasks[event.task_id].apply_event(event)

        elif isinstance(event, TaskUnblocked):
            if event.task_id in self.tasks:
                self.tasks[event.task_id].apply_event(event)

    def can_complete(self) -> bool:
        """Check if the requirement can be completed"""
        if self.status == 'blocked':
            raise ValueError("Cannot complete blocked requirement")
            
        # Check if all tasks are completed
        active_tasks = [task for task in self.tasks.values() if task.status != 'completed']
        if active_tasks:
            raise ValueError("Cannot complete requirement with pending tasks")
            
        return True

    def has_active_tasks(self) -> bool:
        """Check if the requirement has any active tasks"""
        return any(task.status == 'active' for task in self.tasks.values())


@dataclass
class Task:
    """Aggregate for tasks"""
    task_id: UUID
    requirement_id: UUID
    project_id: UUID
    title: str = ''
    description: str = ''
    complexity: str = ''
    status: str = 'active'  # active, blocked, completed
    priority: str = 'medium'
    assignee_id: Optional[UUID] = None
    blocker_description: Optional[str] = None

    def apply_event(self, event):
        """Apply an event to update the aggregate state"""
        if isinstance(event, TaskCreated):
            self.title = event.title
            self.description = event.description
            self.complexity = event.complexity

        elif isinstance(event, TaskCompleted):
            self.status = 'completed'

        elif isinstance(event, TaskAssigned):
            self.assignee_id = event.assignee_id

        elif isinstance(event, TaskPriorityChanged):
            self.priority = event.new_priority

        elif isinstance(event, TaskBlocked):
            self.status = 'blocked'
            self.blocker_description = event.blocker_description

        elif isinstance(event, TaskUnblocked):
            self.status = 'active'
            self.blocker_description = None

    def can_complete(self) -> bool:
        """Check if the task can be completed"""
        return self.status != 'blocked' 