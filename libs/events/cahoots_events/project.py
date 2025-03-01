"""Project domain events"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from .base import Event, EventMetadata


@dataclass
class ProjectCreated(Event):
    """Event when a new project is created"""
    project_id: UUID
    name: str
    description: str
    repository: str
    tech_stack: List[str]
    created_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, name: str, description: str, repository: str,
                 tech_stack: List[str], created_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.name = name
        self.description = description
        self.repository = repository
        self.tech_stack = tech_stack
        self.created_by = created_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class ProjectStatusUpdated(Event):
    """Event when project status is updated"""
    project_id: UUID
    status: str
    reason: str
    updated_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, status: str, reason: str, updated_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.status = status
        self.reason = reason
        self.updated_by = updated_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class ProjectTimelineSet(Event):
    """Event when project timeline is set"""
    project_id: UUID
    start_date: datetime
    target_date: datetime
    milestones: List[Dict]
    set_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, start_date: datetime, target_date: datetime,
                 milestones: List[Dict], set_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.start_date = start_date
        self.target_date = target_date
        self.milestones = milestones
        self.set_by = set_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class RequirementAdded(Event):
    """Event when a requirement is added"""
    project_id: UUID
    requirement_id: UUID
    title: str
    description: str
    priority: str
    dependencies: List[UUID]
    added_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, requirement_id: UUID, title: str, description: str,
                 priority: str, dependencies: List[UUID], added_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.title = title
        self.description = description
        self.priority = priority
        self.dependencies = dependencies
        self.added_by = added_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class RequirementCompleted(Event):
    """Event when a requirement is completed"""
    project_id: UUID
    requirement_id: UUID
    completed_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, requirement_id: UUID, completed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.completed_by = completed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class RequirementBlocked(Event):
    """Event when a requirement is blocked"""
    project_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, requirement_id: UUID, blocker_description: str, blocked_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.blocker_description = blocker_description
        self.blocked_by = blocked_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class RequirementUnblocked(Event):
    """Event when a requirement is unblocked"""
    project_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, requirement_id: UUID, resolution: str, unblocked_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.resolution = resolution
        self.unblocked_by = unblocked_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class RequirementPriorityChanged(Event):
    """Event when requirement priority is changed"""
    project_id: UUID
    requirement_id: UUID
    old_priority: str
    new_priority: str
    reason: str
    changed_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, requirement_id: UUID, old_priority: str,
                 new_priority: str, reason: str, changed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.reason = reason
        self.changed_by = changed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskCreated(Event):
    """Event when a task is created"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    title: str
    description: str
    complexity: str
    created_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID, title: str,
                 description: str, complexity: str, created_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.title = title
        self.description = description
        self.complexity = complexity
        self.created_by = created_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskCompleted(Event):
    """Event when a task is completed"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    completed_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID, completed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.completed_by = completed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskAssigned(Event):
    """Event when a task is assigned"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    assignee_id: UUID
    assigned_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID,
                 assignee_id: UUID, assigned_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.assignee_id = assignee_id
        self.assigned_by = assigned_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskBlocked(Event):
    """Event when a task is blocked"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    blocker_description: str
    blocked_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID,
                 blocker_description: str, blocked_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.blocker_description = blocker_description
        self.blocked_by = blocked_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskUnblocked(Event):
    """Event when a task is unblocked"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    resolution: str
    unblocked_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID,
                 resolution: str, unblocked_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.resolution = resolution
        self.unblocked_by = unblocked_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class TaskPriorityChanged(Event):
    """Event when task priority is changed"""
    project_id: UUID
    task_id: UUID
    requirement_id: UUID
    old_priority: str
    new_priority: str
    reason: str
    changed_by: UUID

    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, task_id: UUID, requirement_id: UUID,
                 old_priority: str, new_priority: str, reason: str, changed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.reason = reason
        self.changed_by = changed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id 