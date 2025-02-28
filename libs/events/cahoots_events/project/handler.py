"""Project management domain handlers"""
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from .commands import (
    CreateProject, UpdateProjectStatus, SetProjectTimeline,
    AddRequirement, CompleteRequirement, BlockRequirement, UnblockRequirement,
    ChangeRequirementPriority, CreateTask, CompleteTask, AssignTask,
    BlockTask, UnblockTask, ChangeTaskPriority
)
from .events import (
    ProjectCreated, ProjectStatusUpdated, ProjectTimelineSet,
    RequirementAdded, RequirementCompleted, RequirementBlocked, RequirementUnblocked,
    RequirementPriorityChanged, TaskCreated, TaskCompleted, TaskAssigned,
    TaskBlocked, TaskUnblocked, TaskPriorityChanged
)
from .repository import ProjectRepository
from ..base import EventMetadata


class ProjectHandler:
    """Handler for project-related commands"""

    def __init__(self, event_store, view_store, project_repository: ProjectRepository):
        self.event_store = event_store
        self.view_store = view_store
        self.project_repository = project_repository

    def handle_create_project(self, cmd: CreateProject) -> List[ProjectCreated]:
        """Handle CreateProject command"""
        # Check if project name is already taken
        existing_project = self.project_repository.get_by_name(cmd.name)
        if existing_project:
            raise ValueError(f"Project with name '{cmd.name}' already exists")

        project_id = uuid4()
        event = ProjectCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=project_id,
            name=cmd.name,
            description=cmd.description,
            repository=cmd.repository,
            tech_stack=cmd.tech_stack,
            created_by=cmd.created_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_update_status(self, cmd: UpdateProjectStatus) -> List[ProjectStatusUpdated]:
        """Handle UpdateProjectStatus command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        if not project.can_change_status(cmd.status):
            raise ValueError(f"Cannot change project status to {cmd.status}")

        event = ProjectStatusUpdated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            status=cmd.status,
            reason=cmd.reason,
            updated_by=cmd.updated_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_set_timeline(self, cmd: SetProjectTimeline) -> List[ProjectTimelineSet]:
        """Handle SetProjectTimeline command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        event = ProjectTimelineSet(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            start_date=cmd.start_date,
            target_date=cmd.target_date,
            milestones=cmd.milestones,
            set_by=cmd.set_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_add_requirement(self, cmd: AddRequirement) -> List[RequirementAdded]:
        """Handle AddRequirement command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        # Check if all dependencies exist
        for dep_id in cmd.dependencies:
            if dep_id not in project.requirements:
                raise ValueError(f"Dependency requirement {dep_id} not found")

        requirement_id = uuid4()
        event = RequirementAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            requirement_id=requirement_id,
            title=cmd.title,
            description=cmd.description,
            priority=cmd.priority,
            dependencies=cmd.dependencies,
            added_by=cmd.added_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_complete_requirement(self, cmd: CompleteRequirement) -> List[RequirementCompleted]:
        """Handle CompleteRequirement command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        if not project.can_complete_requirement(cmd.requirement_id):
            raise ValueError("Cannot complete requirement")

        event = RequirementCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            completed_by=cmd.completed_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_block_requirement(self, cmd: BlockRequirement) -> List[RequirementBlocked]:
        """Handle BlockRequirement command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        if cmd.requirement_id not in project.requirements:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        event = RequirementBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_unblock_requirement(self, cmd: UnblockRequirement) -> List[RequirementUnblocked]:
        """Handle UnblockRequirement command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        if cmd.requirement_id not in project.requirements:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        event = RequirementUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_change_requirement_priority(self, cmd: ChangeRequirementPriority) -> List[RequirementPriorityChanged]:
        """Handle ChangeRequirementPriority command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        event = RequirementPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            old_priority=requirement.priority,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_create_task(self, cmd: CreateTask) -> List[TaskCreated]:
        """Handle CreateTask command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        if cmd.requirement_id not in project.requirements:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        task_id = uuid4()
        event = TaskCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=task_id,
            requirement_id=cmd.requirement_id,
            title=cmd.title,
            description=cmd.description,
            complexity=cmd.complexity,
            created_by=cmd.created_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_complete_task(self, cmd: CompleteTask) -> List[TaskCompleted]:
        """Handle CompleteTask command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        task = requirement.tasks.get(cmd.task_id)
        if not task:
            raise ValueError(f"Task {cmd.task_id} not found")

        if not task.can_complete():
            raise ValueError("Cannot complete blocked task")

        event = TaskCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            completed_by=cmd.completed_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_assign_task(self, cmd: AssignTask) -> List[TaskAssigned]:
        """Handle AssignTask command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        if cmd.task_id not in requirement.tasks:
            raise ValueError(f"Task {cmd.task_id} not found")

        event = TaskAssigned(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            assignee_id=cmd.assignee_id,
            assigned_by=cmd.assigned_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_block_task(self, cmd: BlockTask) -> List[TaskBlocked]:
        """Handle BlockTask command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        if cmd.task_id not in requirement.tasks:
            raise ValueError(f"Task {cmd.task_id} not found")

        event = TaskBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_unblock_task(self, cmd: UnblockTask) -> List[TaskUnblocked]:
        """Handle UnblockTask command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        if cmd.task_id not in requirement.tasks:
            raise ValueError(f"Task {cmd.task_id} not found")

        event = TaskUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_change_task_priority(self, cmd: ChangeTaskPriority) -> List[TaskPriorityChanged]:
        """Handle ChangeTaskPriority command"""
        project = self.project_repository.get_by_id(cmd.project_id)
        if not project:
            raise ValueError(f"No project found with id {cmd.project_id}")

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {cmd.requirement_id} not found")

        task = requirement.tasks.get(cmd.task_id)
        if not task:
            raise ValueError(f"Task {cmd.task_id} not found")

        event = TaskPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            old_priority=task.priority,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event] 