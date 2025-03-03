"""
Project handler for tests
"""

from datetime import datetime
from uuid import uuid4

from ..test_imports import EventMetadata, ProjectCreated


class RequirementAdded:
    """Event when a requirement is added to a project"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        requirement_id,
        title,
        description,
        priority,
        dependencies,
        added_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.title = title
        self.description = description
        self.priority = priority
        self.dependencies = dependencies
        self.added_by = added_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskCreated:
    """Event when a task is created for a requirement"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        requirement_id,
        task_id,
        title,
        description,
        complexity,
        created_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.task_id = task_id
        self.title = title
        self.description = description
        self.complexity = complexity
        self.created_by = created_by

    @property
    def aggregate_id(self):
        return self.project_id


class RequirementCompleted:
    """Event when a requirement is completed"""

    def __init__(self, event_id, timestamp, metadata, project_id, requirement_id, completed_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.completed_by = completed_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskCompleted:
    """Event when a task is completed"""

    def __init__(
        self, event_id, timestamp, metadata, project_id, requirement_id, task_id, completed_by
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.task_id = task_id
        self.completed_by = completed_by

    @property
    def aggregate_id(self):
        return self.project_id


class ProjectTimelineSet:
    """Event when a project timeline is set"""

    def __init__(
        self, event_id, timestamp, metadata, project_id, start_date, target_date, milestones, set_by
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.start_date = start_date
        self.target_date = target_date
        self.milestones = milestones
        self.set_by = set_by

    @property
    def aggregate_id(self):
        return self.project_id


class ProjectStatusUpdated:
    """Event when a project status is updated"""

    def __init__(self, event_id, timestamp, metadata, project_id, status, reason, updated_by):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.status = status
        self.reason = reason
        self.updated_by = updated_by

    @property
    def aggregate_id(self):
        return self.project_id


class RequirementBlocked:
    """Event when a requirement is blocked"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        requirement_id,
        blocker_description,
        blocked_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.blocker_description = blocker_description
        self.blocked_by = blocked_by

    @property
    def aggregate_id(self):
        return self.project_id


class RequirementUnblocked:
    """Event when a requirement is unblocked"""

    def __init__(
        self, event_id, timestamp, metadata, project_id, requirement_id, resolution, unblocked_by
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.resolution = resolution
        self.unblocked_by = unblocked_by

    @property
    def aggregate_id(self):
        return self.project_id


class RequirementPriorityChanged:
    """Event when a requirement priority is changed"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        requirement_id,
        new_priority,
        reason,
        changed_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.new_priority = new_priority
        self.reason = reason
        self.changed_by = changed_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskAssigned:
    """Event when a task is assigned"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        task_id,
        requirement_id,
        assignee_id,
        assigned_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.assignee_id = assignee_id
        self.assigned_by = assigned_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskBlocked:
    """Event when a task is blocked"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        task_id,
        requirement_id,
        blocker_description,
        blocked_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.blocker_description = blocker_description
        self.blocked_by = blocked_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskUnblocked:
    """Event when a task is unblocked"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        task_id,
        requirement_id,
        resolution,
        unblocked_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.resolution = resolution
        self.unblocked_by = unblocked_by

    @property
    def aggregate_id(self):
        return self.project_id


class TaskPriorityChanged:
    """Event when a task priority is changed"""

    def __init__(
        self,
        event_id,
        timestamp,
        metadata,
        project_id,
        task_id,
        requirement_id,
        new_priority,
        reason,
        changed_by,
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata
        self.project_id = project_id
        self.task_id = task_id
        self.requirement_id = requirement_id
        self.new_priority = new_priority
        self.reason = reason
        self.changed_by = changed_by

    @property
    def aggregate_id(self):
        return self.project_id


class ProjectHandler:
    """Handler for project commands in tests"""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store
        self.code_changes_handler = None

    def set_code_changes_handler(self, code_changes_handler):
        """Set the code changes handler"""
        self.code_changes_handler = code_changes_handler

    def handle_create_project(self, cmd):
        """Handle create project command"""
        # Create proper event object
        event = ProjectCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.created_by
            ),
            project_id=cmd.correlation_id,
            name=cmd.name,
            description=cmd.description,
            repository=cmd.repository,
            tech_stack=cmd.tech_stack,
            created_by=cmd.created_by,
        )
        self.event_store.append(event)

        # Import the view class here to avoid circular imports
        from ..views.project_views import ProjectOverviewView

        # Get or create the view
        view = self.view_store.get_view(cmd.correlation_id, ProjectOverviewView)

        # Apply the event to update the view
        view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.correlation_id, view)

        return [event]

    def handle_add_requirement(self, cmd):
        """Handle add requirement command"""
        # Create proper event object
        requirement_id = uuid4()
        event = RequirementAdded(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.added_by
            ),
            project_id=cmd.project_id,
            requirement_id=requirement_id,
            title=cmd.title,
            description=cmd.description,
            priority=cmd.priority,
            dependencies=cmd.dependencies,
            added_by=cmd.added_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import ProjectOverviewView, RequirementsView

        # Get or create the views
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Apply the event to update the views
        overview_view.apply_event(event)
        requirements_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, overview_view)
        self.view_store.save_view(cmd.project_id, requirements_view)

        return [event]

    def handle_create_task(self, cmd):
        """Handle create task command"""
        # Create proper event object
        task_id = uuid4()
        event = TaskCreated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.created_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            task_id=task_id,
            title=cmd.title,
            description=cmd.description,
            complexity=cmd.complexity,
            created_by=cmd.created_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import (
            ProjectOverviewView,
            RequirementsView,
            TaskBoardView,
        )

        # Get or create the views
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        overview_view.apply_event(event)
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, overview_view)
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_complete_task(self, cmd):
        """Handle complete task command"""
        # Create proper event object
        event = TaskCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.completed_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            task_id=cmd.task_id,
            completed_by=cmd.completed_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import (
            ProjectOverviewView,
            RequirementsView,
            TaskBoardView,
        )

        # Get or create the views
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        overview_view.apply_event(event)
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, overview_view)
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_complete_requirement(self, cmd):
        """Handle complete requirement command"""
        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView

        # Get the requirements view
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Check if the requirement exists
        if cmd.requirement_id not in requirements_view.requirements:
            raise ValueError("Requirement not found")

        # Check if the requirement is blocked
        requirement = requirements_view.requirements[cmd.requirement_id]
        if requirement["status"] == "blocked":
            raise ValueError("Cannot complete blocked requirement")

        # Check if all tasks are completed
        active_tasks = [task for task in requirement["tasks"] if task["status"] == "active"]
        if active_tasks:
            raise ValueError("Cannot complete requirement with pending tasks")

        # Create proper event object
        event = RequirementCompleted(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.completed_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            completed_by=cmd.completed_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import ProjectOverviewView

        # Get or create the views
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)

        # Apply the event to update the views
        overview_view.apply_event(event)
        requirements_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, overview_view)
        self.view_store.save_view(cmd.project_id, requirements_view)

        return [event]

    def handle_set_timeline(self, cmd):
        """Handle set timeline command"""
        # Create proper event object
        event = ProjectTimelineSet(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.set_by
            ),
            project_id=cmd.project_id,
            start_date=cmd.start_date,
            target_date=cmd.target_date,
            milestones=cmd.milestones,
            set_by=cmd.set_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import ProjectOverviewView

        # Get or create the view
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)

        # Apply the event to update the view
        overview_view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, overview_view)

        return [event]

    def handle_update_status(self, cmd):
        """Handle update status command"""
        # Import the view classes here to avoid circular imports
        from ..views.project_views import ProjectOverviewView, RequirementsView

        # Get the views
        overview_view = self.view_store.get_view(cmd.project_id, ProjectOverviewView)
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Check if trying to complete a project with active requirements
        if cmd.status == "completed":
            active_requirements = [
                req for req in requirements_view.requirements.values() if req["status"] == "active"
            ]
            if active_requirements:
                raise ValueError("Cannot complete project with active requirements")

        # Create proper event object
        event = ProjectStatusUpdated(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.updated_by
            ),
            project_id=cmd.project_id,
            status=cmd.status,
            reason=cmd.reason,
            updated_by=cmd.updated_by,
        )
        self.event_store.append(event)

        # Apply the event to update the view
        overview_view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, overview_view)

        return [event]

    def handle_block_requirement(self, cmd):
        """Handle block requirement command"""
        # Create proper event object
        event = RequirementBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.blocked_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView

        # Get or create the view
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Apply the event to update the view
        requirements_view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, requirements_view)

        return [event]

    def handle_unblock_requirement(self, cmd):
        """Handle unblock requirement command"""
        # Create proper event object
        event = RequirementUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.unblocked_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView

        # Get or create the view
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Apply the event to update the view
        requirements_view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, requirements_view)

        return [event]

    def handle_change_requirement_priority(self, cmd):
        """Handle change requirement priority command"""
        # Create proper event object
        event = RequirementPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.changed_by
            ),
            project_id=cmd.project_id,
            requirement_id=cmd.requirement_id,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView

        # Get or create the view
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)

        # Apply the event to update the view
        requirements_view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, requirements_view)

        return [event]

    def handle_assign_task(self, cmd):
        """Handle assign task command"""
        # Create proper event object
        event = TaskAssigned(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.assigned_by
            ),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            assignee_id=cmd.assignee_id,
            assigned_by=cmd.assigned_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView, TaskBoardView

        # Get or create the views
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_block_task(self, cmd):
        """Handle block task command"""
        # Create proper event object
        event = TaskBlocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.blocked_by
            ),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            blocker_description=cmd.blocker_description,
            blocked_by=cmd.blocked_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView, TaskBoardView

        # Get or create the views
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_unblock_task(self, cmd):
        """Handle unblock task command"""
        # Create proper event object
        event = TaskUnblocked(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.unblocked_by
            ),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            resolution=cmd.resolution,
            unblocked_by=cmd.unblocked_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView, TaskBoardView

        # Get or create the views
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_change_task_priority(self, cmd):
        """Handle change task priority command"""
        # Create proper event object
        event = TaskPriorityChanged(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(
                schema_version=1, correlation_id=cmd.correlation_id, actor_id=cmd.changed_by
            ),
            project_id=cmd.project_id,
            task_id=cmd.task_id,
            requirement_id=cmd.requirement_id,
            new_priority=cmd.new_priority,
            reason=cmd.reason,
            changed_by=cmd.changed_by,
        )
        self.event_store.append(event)

        # Import the view classes here to avoid circular imports
        from ..views.project_views import RequirementsView, TaskBoardView

        # Get or create the views
        requirements_view = self.view_store.get_view(cmd.project_id, RequirementsView)
        task_board_view = self.view_store.get_view(cmd.project_id, TaskBoardView)

        # Apply the event to update the views
        requirements_view.apply_event(event)
        task_board_view.apply_event(event)

        # Save the updated views
        self.view_store.save_view(cmd.project_id, requirements_view)
        self.view_store.save_view(cmd.project_id, task_board_view)

        return [event]

    def handle_propose_code_change(self, cmd):
        """Handle propose code change command by delegating to code changes handler"""
        if self.code_changes_handler is None:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_propose_code_change(cmd)

    def handle_review_code_change(self, cmd):
        """Handle review code change command by delegating to code changes handler"""
        if self.code_changes_handler is None:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_review_code_change(cmd)

    def handle_implement_code_change(self, cmd):
        """Handle implement code change command by delegating to code changes handler"""
        if self.code_changes_handler is None:
            raise ValueError("Code changes handler not set")
        return self.code_changes_handler.handle_implement_code_change(cmd)
