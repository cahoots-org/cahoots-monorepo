from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ..domain.aggregates import Project
from ..domain.events import Event, EventMetadata
from ..domain.commands import (
    CreateProject, AddRequirement, CompleteRequirement,
    CreateTask, CompleteTask, SetProjectTimeline,
    UpdateProjectStatus, BlockRequirement, UnblockRequirement,
    ChangeRequirementPriority, AssignTask, BlockTask,
    UnblockTask, ChangeTaskPriority
)
from ..domain.events import (
    ProjectCreated, ProjectStatusUpdated, ProjectTimelineSet,
    RequirementAdded, RequirementCompleted, RequirementPriorityChanged,
    RequirementBlocked, RequirementUnblocked,
    TaskCreated, TaskCompleted, TaskAssigned, TaskPriorityChanged,
    TaskBlocked, TaskUnblocked
)
from ..domain.code_changes.commands import (
    ProposeCodeChange, ReviewCodeChange, ImplementCodeChange
)


class ProjectHandler:
    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store
        self.code_changes_handler = None

    def set_code_changes_handler(self, handler):
        self.code_changes_handler = handler

    def handle_propose_code_change(self, cmd: ProposeCodeChange) -> List[Event]:
        """Handle ProposeCodeChange command by delegating to code changes handler"""
        if not self.code_changes_handler:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_propose_code_change(cmd)

    def handle_review_code_change(self, cmd: ReviewCodeChange) -> List[Event]:
        """Handle ReviewCodeChange command by delegating to code changes handler"""
        if not self.code_changes_handler:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_review_code_change(cmd)

    def handle_implement_code_change(self, cmd: ImplementCodeChange) -> List[Event]:
        """Handle ImplementCodeChange command by delegating to code changes handler"""
        if not self.code_changes_handler:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_implement_code_change(cmd)

    def handle_create_project(self, cmd: CreateProject) -> List[ProjectCreated]:
        """Handle CreateProject command"""
        project_id = uuid4()
        project = Project(project_id=project_id)

        event = ProjectCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=project_id,
            name=cmd.name,
            description=cmd.description,
            repository=cmd.repository,
            tech_stack=cmd.tech_stack,
            created_by=cmd.created_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_update_status(self, cmd: UpdateProjectStatus) -> List[ProjectStatusUpdated]:
        """Handle UpdateProjectStatus command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        if not project.can_change_status(cmd.status):
            raise ValueError("Cannot complete project with active requirements")

        event = ProjectStatusUpdated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            status=cmd.status,
            reason=cmd.reason,
            updated_by=cmd.updated_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_set_timeline(self, cmd: SetProjectTimeline) -> List[ProjectTimelineSet]:
        """Handle SetProjectTimeline command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        event = ProjectTimelineSet(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            start_date=cmd.start_date,
            target_date=cmd.target_date,
            milestones=cmd.milestones,
            set_by=cmd.set_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_add_requirement(self, cmd: AddRequirement) -> List[RequirementAdded]:
        """Handle AddRequirement command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        requirement_id = uuid4()
        event = RequirementAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            requirement_id=requirement_id,
            title=cmd.title,
            description=cmd.description,
            priority=cmd.priority,
            dependencies=cmd.dependencies,
            added_by=cmd.added_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_complete_requirement(self, cmd: CompleteRequirement) -> List[Event]:
        """Handle CompleteRequirement command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        if not project.can_complete_requirement(cmd.requirement_id):
            raise ValueError("Cannot complete requirement with pending tasks")

        requirement_completed_event = RequirementCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            completed_by=cmd.completed_by
        )
        project.apply_event(requirement_completed_event)

        self.event_store.append(requirement_completed_event)
        self.view_store.apply_event(requirement_completed_event)

        # Check if all requirements are completed and update project status
        if project.active_requirements == 0:
            project_status_event = ProjectStatusUpdated(
                event_id=uuid4(),
                timestamp=datetime.utcnow(),
                metadata=EventMetadata(correlation_id=cmd.correlation_id),
                project_id=cmd.project_id,
                status='completed',
                reason='All requirements completed',
                updated_by=cmd.completed_by
            )
            project.apply_event(project_status_event)
            self.event_store.append(project_status_event)
            self.view_store.apply_event(project_status_event)
            return [requirement_completed_event, project_status_event]

        return [requirement_completed_event]

    def handle_block_requirement(self, cmd: BlockRequirement) -> List[RequirementBlocked]:
        """Handle BlockRequirement command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        event = RequirementBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_unblock_requirement(self, cmd: UnblockRequirement) -> List[RequirementUnblocked]:
        """Handle UnblockRequirement command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        event = RequirementUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_change_requirement_priority(self, cmd: ChangeRequirementPriority) -> List[RequirementPriorityChanged]:
        """Handle ChangeRequirementPriority command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"No requirement found with id {cmd.requirement_id}")

        event = RequirementPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            old_priority=requirement.priority,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_create_task(self, cmd: CreateTask) -> List[TaskCreated]:
        """Handle CreateTask command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        task_id = uuid4()
        event = TaskCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=task_id,
            requirement_id=cmd.requirement_id,
            title=cmd.title,
            description=cmd.description,
            complexity=cmd.complexity,
            created_by=cmd.created_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_complete_task(self, cmd: CompleteTask) -> List[TaskCompleted]:
        """Handle CompleteTask command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"No requirement found with id {cmd.requirement_id}")

        task = requirement.tasks.get(cmd.task_id)
        if not task:
            raise ValueError(f"No task found with id {cmd.task_id}")

        if not task.can_complete():
            raise ValueError("Cannot complete blocked task")

        task_completed_event = TaskCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            completed_by=cmd.completed_by
        )
        project.apply_event(task_completed_event)

        self.event_store.append(task_completed_event)
        self.view_store.apply_event(task_completed_event)

        # Check if all tasks are completed and requirement is not already completed
        if requirement.status != 'completed' and all(t.status == 'completed' for t in requirement.tasks.values()):
            requirement_completed_event = RequirementCompleted(
                event_id=uuid4(),
                timestamp=datetime.utcnow(),
                metadata=EventMetadata(correlation_id=cmd.correlation_id),
                project_id=cmd.project_id,
                requirement_id=cmd.requirement_id,
                completed_by=cmd.completed_by
            )
            project.apply_event(requirement_completed_event)
            self.event_store.append(requirement_completed_event)
            self.view_store.apply_event(requirement_completed_event)
            return [task_completed_event, requirement_completed_event]

        return [task_completed_event]

    def handle_assign_task(self, cmd: AssignTask) -> List[TaskAssigned]:
        """Handle AssignTask command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"No requirement found with id {cmd.requirement_id}")

        task = requirement.tasks.get(cmd.task_id)
        if not task:
            raise ValueError(f"No task found with id {cmd.task_id}")

        event = TaskAssigned(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            assignee_id=cmd.assignee_id,
            assigned_by=cmd.assigned_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_block_task(self, cmd: BlockTask) -> List[TaskBlocked]:
        """Handle BlockTask command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        event = TaskBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_unblock_task(self, cmd: UnblockTask) -> List[TaskUnblocked]:
        """Handle UnblockTask command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        event = TaskUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_change_task_priority(self, cmd: ChangeTaskPriority) -> List[TaskPriorityChanged]:
        """Handle ChangeTaskPriority command"""
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        project = Project(project_id=cmd.project_id)
        for event in events:
            project.apply_event(event)

        requirement = project.requirements.get(cmd.requirement_id)
        if not requirement:
            raise ValueError(f"No requirement found with id {cmd.requirement_id}")

        task = requirement.tasks.get(cmd.task_id)
        if not task:
            raise ValueError(f"No task found with id {cmd.task_id}")

        event = TaskPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            old_priority=task.priority,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by
        )
        project.apply_event(event)

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event] 