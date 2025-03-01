from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from .events import (
    ProjectCreated, ProjectStatusUpdated, ProjectTimelineSet,
    RequirementAdded, RequirementCompleted, RequirementPriorityChanged,
    RequirementBlocked, RequirementUnblocked,
    TaskCreated, TaskCompleted, TaskAssigned, TaskPriorityChanged,
    TaskBlocked, TaskUnblocked,
    OrganizationCreated, OrganizationNameUpdated, OrganizationMemberAdded,
    OrganizationMemberRemoved, TeamCreated, TeamMemberAdded, TeamMemberRemoved,
    TeamMemberRoleChanged, TeamArchived
)


@dataclass
class ProjectOverviewView:
    """Overview of project status"""
    project_id: UUID
    name: str = ''
    description: str = ''
    repository: str = ''
    tech_stack: List[str] = field(default_factory=list)
    status: str = 'planning'
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    milestones: List[Dict] = field(default_factory=list)
    active_requirements: int = 0
    completed_requirements: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0

    def __init__(self, entity_id: UUID):
        self.project_id = entity_id

    def apply_event(self, event):
        """Update view based on events"""
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
            self.active_requirements += 1

        elif isinstance(event, RequirementCompleted):
            self.active_requirements -= 1
            self.completed_requirements += 1

        elif isinstance(event, TaskCreated):
            self.active_tasks += 1

        elif isinstance(event, TaskCompleted):
            self.active_tasks -= 1
            self.completed_tasks += 1


@dataclass
class RequirementsView:
    """View of project requirements"""
    project_id: UUID
    requirements: Dict[UUID, Dict] = field(default_factory=dict)
    requirement_dependencies: Dict[UUID, List[UUID]] = field(default_factory=dict)

    def __init__(self, entity_id: UUID):
        self.project_id = entity_id

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, RequirementAdded):
            self.requirements[event.requirement_id] = {
                'id': event.requirement_id,
                'title': event.title,
                'description': event.description,
                'priority': event.priority,
                'status': 'active',
                'tasks': [],
                'dependencies': event.dependencies,
                'blocker_description': None
            }
            # Store dependencies in both places
            self.requirement_dependencies[event.requirement_id] = event.dependencies.copy() if event.dependencies else []

        elif isinstance(event, RequirementCompleted):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]['status'] = 'completed'

        elif isinstance(event, RequirementPriorityChanged):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]['priority'] = event.new_priority

        elif isinstance(event, RequirementBlocked):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]['status'] = 'blocked'
                self.requirements[event.requirement_id]['blocker_description'] = event.blocker_description

        elif isinstance(event, RequirementUnblocked):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]['status'] = 'active'
                self.requirements[event.requirement_id]['blocker_description'] = None

        elif isinstance(event, TaskCreated):
            if event.requirement_id in self.requirements:
                self.requirements[event.requirement_id]['tasks'].append({
                    'id': event.task_id,
                    'title': event.title,
                    'description': event.description,
                    'complexity': event.complexity,
                    'status': 'active',
                    'priority': 'medium',
                    'assignee_id': None,
                    'blocker_description': None
                })

        elif isinstance(event, TaskCompleted):
            if event.requirement_id in self.requirements:
                requirement = self.requirements[event.requirement_id]
                for task in requirement['tasks']:
                    if task['id'] == event.task_id:
                        task['status'] = 'completed'
                        break

        elif isinstance(event, TaskAssigned):
            if event.requirement_id in self.requirements:
                for task in self.requirements[event.requirement_id]['tasks']:
                    if task['id'] == event.task_id:
                        task['assignee_id'] = event.assignee_id
                        break

        elif isinstance(event, TaskPriorityChanged):
            if event.requirement_id in self.requirements:
                for task in self.requirements[event.requirement_id]['tasks']:
                    if task['id'] == event.task_id:
                        task['priority'] = event.new_priority
                        break

        elif isinstance(event, TaskBlocked):
            if event.requirement_id in self.requirements:
                for task in self.requirements[event.requirement_id]['tasks']:
                    if task['id'] == event.task_id:
                        task['status'] = 'blocked'
                        task['blocker_description'] = event.blocker_description
                        break

        elif isinstance(event, TaskUnblocked):
            if event.requirement_id in self.requirements:
                for task in self.requirements[event.requirement_id]['tasks']:
                    if task['id'] == event.task_id:
                        task['status'] = 'active'
                        task['blocker_description'] = None
                        break

    def get_requirement(self, requirement_id: UUID) -> Optional[Dict]:
        """Get requirement details"""
        return self.requirements.get(requirement_id)

    def get_dependencies_for(self, requirement_id: UUID) -> List[Dict]:
        """Get list of requirements that this requirement depends on"""
        dependencies = []
        if requirement_id in self.requirement_dependencies:
            for dep_id in self.requirement_dependencies[requirement_id]:
                if dep_id in self.requirements:
                    dependencies.append(self.requirements[dep_id])
        return dependencies

    def get_dependents_for(self, requirement_id: UUID) -> List[Dict]:
        """Get list of requirements that depend on this requirement"""
        dependents = []
        for req_id, deps in self.requirement_dependencies.items():
            if requirement_id in deps and req_id in self.requirements:
                dependents.append(self.requirements[req_id])
        return dependents


@dataclass
class TaskBoardView:
    """Kanban-style view of tasks"""
    project_id: UUID
    columns: Dict[str, List[Dict]] = field(default_factory=lambda: {
        'backlog': [],
        'in_progress': [],
        'review': [],
        'done': []
    })

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, TaskCreated):
            task = {
                'id': event.task_id,
                'requirement_id': event.requirement_id,
                'title': event.title,
                'description': event.description,
                'complexity': event.complexity,
                'status': 'active',
                'priority': 'medium',
                'assignee_id': None,
                'blocker_description': None
            }
            self.columns['backlog'].append(task)

        elif isinstance(event, TaskCompleted):
            self._move_task_to_column(event.task_id, 'done')

        elif isinstance(event, TaskAssigned):
            self._update_task(event.task_id, {'assignee_id': event.assignee_id})

        elif isinstance(event, TaskPriorityChanged):
            self._update_task(event.task_id, {'priority': event.new_priority})

        elif isinstance(event, TaskBlocked):
            self._update_task(event.task_id, {
                'status': 'blocked',
                'blocker_description': event.blocker_description
            })

        elif isinstance(event, TaskUnblocked):
            self._update_task(event.task_id, {
                'status': 'active',
                'blocker_description': None
            })

    def _move_task_to_column(self, task_id: UUID, target_column: str):
        """Move a task to a specific column"""
        task = None
        source_column = None

        # Find the task
        for col_name, tasks in self.columns.items():
            for t in tasks:
                if t['id'] == task_id:
                    task = t
                    source_column = col_name
                    break
            if task:
                break

        # Move the task
        if task and source_column:
            self.columns[source_column].remove(task)
            self.columns[target_column].append(task)

    def _update_task(self, task_id: UUID, updates: Dict):
        """Update task properties"""
        for tasks in self.columns.values():
            for task in tasks:
                if task['id'] == task_id:
                    task.update(updates)
                    break


@dataclass
class CodeChangeView:
    """Projection of code changes for a project"""
    project_id: UUID
    pending_changes: Dict[UUID, Dict] = field(default_factory=dict)
    implemented_changes: Dict[UUID, Dict] = field(default_factory=dict)
    changes_by_file: Dict[str, List[UUID]] = field(default_factory=dict)

    def __init__(self, entity_id: UUID):
        self.project_id = entity_id

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, CodeChangeProposed):
            change_data = {
                'change_id': event.change_id,
                'task_id': event.task_id,
                'files': event.files,
                'description': event.description,
                'status': 'proposed',
                'proposed_by': event.proposed_by,
                'timestamp': event.timestamp
            }
            self.pending_changes[event.change_id] = change_data
            
            # Update changes by file index
            for file in event.files:
                if file not in self.changes_by_file:
                    self.changes_by_file[file] = []
                self.changes_by_file[file].append(event.change_id)

        elif isinstance(event, CodeChangeReviewed):
            if event.change_id in self.pending_changes:
                self.pending_changes[event.change_id].update({
                    'status': event.status,
                    'reviewer_id': event.reviewer_id,
                    'review_timestamp': event.timestamp,
                    'comments': event.comments
                })

        elif isinstance(event, CodeChangeImplemented):
            if event.change_id in self.pending_changes:
                change_data = self.pending_changes.pop(event.change_id)
                change_data.update({
                    'status': 'implemented',
                    'implemented_by': event.implemented_by,
                    'implementation_timestamp': event.timestamp,
                    'final_diff': event.final_diff
                })
                self.implemented_changes[event.change_id] = change_data

    def get_changes_for_file(self, file_path: str) -> List[Dict]:
        """Get all changes affecting a specific file"""
        change_ids = self.changes_by_file.get(file_path, [])
        changes = []
        for change_id in change_ids:
            if change_id in self.pending_changes:
                changes.append(self.pending_changes[change_id])
            elif change_id in self.implemented_changes:
                changes.append(self.implemented_changes[change_id])
        return changes

    def get_pending_reviews(self) -> List[Dict]:
        """Get all changes pending review"""
        return [
            change for change in self.pending_changes.values()
            if change['status'] == 'proposed'
        ]

    def get_changes_by_status(self, status: str) -> List[Dict]:
        """Get all changes with a specific status"""
        changes = []
        if status == 'implemented':
            changes.extend(self.implemented_changes.values())
        else:
            changes.extend([
                change for change in self.pending_changes.values()
                if change['status'] == status
            ])
        return changes


@dataclass
class OrganizationView:
    """View of organization details and members"""
    organization_id: UUID
    name: str = ''
    members: Dict[UUID, Dict] = field(default_factory=dict)
    teams: Dict[UUID, Dict] = field(default_factory=dict)

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, OrganizationCreated):
            self.name = event.name

        elif isinstance(event, OrganizationNameUpdated):
            self.name = event.new_name

        elif isinstance(event, OrganizationMemberAdded):
            self.members[event.member_id] = {
                'id': event.member_id,
                'role': event.role,
                'added_by': event.added_by,
                'added_at': event.timestamp
            }

        elif isinstance(event, OrganizationMemberRemoved):
            if event.member_id in self.members:
                del self.members[event.member_id]

        elif isinstance(event, TeamCreated):
            self.teams[event.team_id] = {
                'id': event.team_id,
                'name': event.name,
                'description': event.description,
                'created_by': event.created_by,
                'created_at': event.timestamp,
                'status': 'active'
            }

        elif isinstance(event, TeamArchived):
            if event.team_id in self.teams:
                self.teams[event.team_id]['status'] = 'archived'


@dataclass
class TeamView:
    """View of team details and members"""
    team_id: UUID
    name: str = ''
    description: str = ''
    members: Dict[UUID, Dict] = field(default_factory=dict)
    status: str = 'active'

    def apply_event(self, event):
        """Update view based on events"""
        if isinstance(event, TeamCreated):
            self.name = event.name
            self.description = event.description

        elif isinstance(event, TeamMemberAdded):
            self.members[event.member_id] = {
                'id': event.member_id,
                'role': event.role,
                'added_by': event.added_by,
                'added_at': event.timestamp
            }

        elif isinstance(event, TeamMemberRemoved):
            if event.member_id in self.members:
                del self.members[event.member_id]

        elif isinstance(event, TeamMemberRoleChanged):
            if event.member_id in self.members:
                self.members[event.member_id]['role'] = event.new_role

        elif isinstance(event, TeamArchived):
            self.status = 'archived'