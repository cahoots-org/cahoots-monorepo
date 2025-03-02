"""
Project view classes for tests
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID


class ProjectOverviewView:
    """Project overview view"""

    def __init__(self, entity_id=None):
        self.id = entity_id
        self.name = ""
        self.description = ""
        self.repository = ""
        self.tech_stack = []
        self.status = "planning"
        self.timeline = {}
        self.created_by = None
        self.created_at = None

        # Project timeline attributes
        self.start_date = None
        self.target_date = None
        self.milestones = []

        # Project statistics
        self.active_requirements = 0
        self.completed_requirements = 0
        self.active_tasks = 0
        self.completed_tasks = 0

    def apply_event(self, event):
        """Apply an event to update this view"""
        event_type = event.__class__.__name__

        # Handle project created
        if event_type == "ProjectCreated":
            self.name = event.name
            self.description = event.description
            self.repository = event.repository
            self.tech_stack = event.tech_stack
            self.created_by = event.created_by
            self.created_at = event.timestamp

        # Handle requirement added
        elif event_type == "RequirementAdded":
            self.active_requirements += 1

        # Handle requirement completed
        elif event_type == "RequirementCompleted":
            self.active_requirements -= 1
            self.completed_requirements += 1

        # Handle task created
        elif event_type == "TaskCreated":
            self.active_tasks += 1

        # Handle task completed
        elif event_type == "TaskCompleted":
            self.active_tasks -= 1
            self.completed_tasks += 1

        # Handle timeline set
        elif event_type == "ProjectTimelineSet":
            self.start_date = event.start_date
            self.target_date = event.target_date
            self.milestones = event.milestones

        # Handle status updated
        elif event_type == "ProjectStatusUpdated":
            self.status = event.status


class RequirementsView:
    """Requirements view"""

    def __init__(self, entity_id=None):
        self.project_id = entity_id
        self.requirements = {}
        self.requirement_dependencies = {}

    def apply_event(self, event):
        """Apply an event to update this view"""
        event_type = event.__class__.__name__

        # Handle requirement added
        if event_type == "RequirementAdded":
            self.requirements[event.requirement_id] = {
                "id": event.requirement_id,
                "title": event.title,
                "description": event.description,
                "priority": event.priority,
                "status": "active",
                "dependencies": event.dependencies,
                "tasks": [],
                "added_by": event.added_by,
                "added_at": event.timestamp,
            }

            # Update dependencies mapping
            if event.dependencies:
                for dep_id in event.dependencies:
                    if dep_id not in self.requirement_dependencies:
                        self.requirement_dependencies[dep_id] = []
                    self.requirement_dependencies[dep_id].append(event.requirement_id)

        # Handle task created
        elif event_type == "TaskCreated":
            if event.requirement_id in self.requirements:
                task = {
                    "id": event.task_id,
                    "title": event.title,
                    "description": event.description,
                    "complexity": event.complexity,
                    "status": "active",
                    "assignee": None,
                    "assignee_id": None,
                    "created_by": event.created_by,
                    "created_at": event.timestamp,
                }
                self.requirements[event.requirement_id]["tasks"].append(task)

        # Handle requirement completed
        elif event_type == "RequirementCompleted":
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]["status"] = "completed"

        # Handle requirement blocked
        elif event_type == "RequirementBlocked":
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]["status"] = "blocked"
                self.requirements[event.requirement_id][
                    "blocker_description"
                ] = event.blocker_description

        # Handle requirement unblocked
        elif event_type == "RequirementUnblocked":
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]["status"] = "active"
                self.requirements[event.requirement_id]["blocker_description"] = None

        # Handle requirement priority changed
        elif event_type == "RequirementPriorityChanged":
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]["priority"] = event.new_priority

        # Handle task assigned
        elif event_type == "TaskAssigned":
            for req in self.requirements.values():
                for task in req["tasks"]:
                    if task["id"] == event.task_id:
                        task["assignee_id"] = event.assignee_id

        # Handle task blocked
        elif event_type == "TaskBlocked":
            for req in self.requirements.values():
                for task in req["tasks"]:
                    if task["id"] == event.task_id:
                        task["status"] = "blocked"
                        task["blocker_description"] = event.blocker_description

        # Handle task unblocked
        elif event_type == "TaskUnblocked":
            for req in self.requirements.values():
                for task in req["tasks"]:
                    if task["id"] == event.task_id:
                        task["status"] = "active"
                        task["blocker_description"] = None

        # Handle task completed
        elif event_type == "TaskCompleted":
            for req in self.requirements.values():
                for task in req["tasks"]:
                    if task["id"] == event.task_id:
                        task["status"] = "completed"

        # Handle task priority changed
        elif event_type == "TaskPriorityChanged":
            for req in self.requirements.values():
                for task in req["tasks"]:
                    if task["id"] == event.task_id:
                        task["priority"] = event.new_priority


class TaskBoardView:
    """Task board view"""

    def __init__(self, entity_id=None):
        self.project_id = entity_id
        self.tasks = {}

    def apply_event(self, event):
        """Apply an event to update this view"""
        event_type = event.__class__.__name__

        # Handle task created
        if event_type == "TaskCreated":
            self.tasks[event.task_id] = {
                "id": event.task_id,
                "requirement_id": event.requirement_id,
                "title": event.title,
                "description": event.description,
                "complexity": event.complexity,
                "status": "active",
                "assignee": None,
                "assignee_id": None,
                "created_by": event.created_by,
                "created_at": event.timestamp,
            }

        # Handle task assigned
        elif event_type == "TaskAssigned":
            if event.task_id in self.tasks:
                self.tasks[event.task_id]["assignee_id"] = event.assignee_id

        # Handle task blocked
        elif event_type == "TaskBlocked":
            if event.task_id in self.tasks:
                self.tasks[event.task_id]["status"] = "blocked"
                self.tasks[event.task_id]["blocker_description"] = event.blocker_description

        # Handle task unblocked
        elif event_type == "TaskUnblocked":
            if event.task_id in self.tasks:
                self.tasks[event.task_id]["status"] = "active"
                self.tasks[event.task_id]["blocker_description"] = None

        # Handle task completed
        elif event_type == "TaskCompleted":
            if event.task_id in self.tasks:
                self.tasks[event.task_id]["status"] = "completed"

        # Handle task priority changed
        elif event_type == "TaskPriorityChanged":
            if event.task_id in self.tasks:
                self.tasks[event.task_id]["priority"] = event.new_priority
