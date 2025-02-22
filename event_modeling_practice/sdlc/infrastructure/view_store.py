from typing import Dict, Optional, Type, TypeVar, Generic
from uuid import UUID

from sdlc.domain.views import ProjectOverviewView, RequirementsView, TaskBoardView
from sdlc.domain.code_changes.views import CodeChangesView
from sdlc.domain.organization.views import (
    OrganizationDetailsView, OrganizationMembersView,
    OrganizationAuditLogView
)
from sdlc.domain.team.views import TeamView
from sdlc.domain.auth.views import UserView, SessionView


T = TypeVar('T')

class ViewCollection(Generic[T]):
    """Generic collection for managing views of a specific type"""
    def __init__(self):
        self.views: Dict[UUID, T] = {}

    def get(self, entity_id: UUID) -> Optional[T]:
        return self.views.get(entity_id)

    def add(self, entity_id: UUID, view: T) -> T:
        self.views[entity_id] = view
        return view

class InMemoryViewStore:
    """In-memory implementation of view store"""

    def __init__(self):
        self.project_views = ViewCollection[ProjectOverviewView]()
        self.requirements_views = ViewCollection[RequirementsView]()
        self.task_board_views = ViewCollection[TaskBoardView]()
        self.organization_details_views = ViewCollection[OrganizationDetailsView]()
        self.organization_members_views = ViewCollection[OrganizationMembersView]()
        self.organization_audit_log_views = ViewCollection[OrganizationAuditLogView]()
        self.team_views = ViewCollection[TeamView]()
        self.user_views = ViewCollection[UserView]()
        self.session_views = ViewCollection[SessionView]()
        self.code_changes_views = ViewCollection[CodeChangesView]()

    def create_view(self, view_type: Type[T], entity_id: UUID, **kwargs) -> T:
        """Create a new view instance"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            raise ValueError(f"Unknown view type: {view_type}")

        if view_type == TeamView:
            view = TeamView(team_id=entity_id, **kwargs)
        elif view_type == ProjectOverviewView:
            view = ProjectOverviewView(project_id=entity_id)
        elif view_type == RequirementsView:
            view = RequirementsView(project_id=entity_id)
        elif view_type == TaskBoardView:
            view = TaskBoardView(project_id=entity_id)
        elif view_type == OrganizationDetailsView:
            view = OrganizationDetailsView(organization_id=entity_id)
        elif view_type == OrganizationMembersView:
            view = OrganizationMembersView(organization_id=entity_id)
        elif view_type == OrganizationAuditLogView:
            view = OrganizationAuditLogView(organization_id=entity_id)
        elif view_type == UserView:
            view = UserView(user_id=entity_id)
        elif view_type == SessionView:
            view = SessionView(user_id=entity_id)
        elif view_type == CodeChangesView:
            view = CodeChangesView(project_id=entity_id)
        else:
            raise ValueError(f"Unknown view type: {view_type}")

        return view_collection.add(entity_id, view)

    def get_or_create_view(self, view_type: Type[T], entity_id: UUID, **kwargs) -> T:
        """Get or create a view for the given entity"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            raise ValueError(f"Unknown view type: {view_type}")

        view = view_collection.get(entity_id)
        if view is None:
            view = self.create_view(view_type, entity_id, **kwargs)
        return view

    def get_view(self, entity_id: UUID, view_type: Type[T]) -> Optional[T]:
        """Get a view by type and entity ID"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            return None
        return view_collection.get(entity_id)

    def _get_collection_for_type(self, view_type: Type[T]) -> Optional[ViewCollection[T]]:
        """Get the appropriate view collection for a view type"""
        if view_type == ProjectOverviewView:
            return self.project_views
        elif view_type == RequirementsView:
            return self.requirements_views
        elif view_type == TaskBoardView:
            return self.task_board_views
        elif view_type == OrganizationDetailsView:
            return self.organization_details_views
        elif view_type == OrganizationMembersView:
            return self.organization_members_views
        elif view_type == OrganizationAuditLogView:
            return self.organization_audit_log_views
        elif view_type == TeamView:
            return self.team_views
        elif view_type == UserView:
            return self.user_views
        elif view_type == SessionView:
            return self.session_views
        elif view_type == CodeChangesView:
            return self.code_changes_views
        return None

    def apply_event(self, event):
        """Apply an event to all relevant views"""
        if hasattr(event, 'project_id'):
            # Project events
            project_id = event.project_id
            self.get_or_create_view(ProjectOverviewView, project_id).apply_event(event)
            self.get_or_create_view(RequirementsView, project_id).apply_event(event)
            self.get_or_create_view(TaskBoardView, project_id).apply_event(event)
            self.get_or_create_view(CodeChangesView, project_id).apply_event(event)

        elif hasattr(event, 'organization_id'):
            # Organization events
            org_id = event.organization_id
            self.get_or_create_view(OrganizationDetailsView, org_id).apply_event(event)
            self.get_or_create_view(OrganizationMembersView, org_id).apply_event(event)
            self.get_or_create_view(OrganizationAuditLogView, org_id).apply_event(event)

        elif hasattr(event, 'team_id'):
            # Team events
            team_id = event.team_id
            self.get_or_create_view(TeamView, team_id).apply_event(event)

        elif hasattr(event, 'user_id'):
            # User events
            user_id = event.user_id
            self.get_or_create_view(UserView, user_id).apply_event(event)
            if hasattr(event, 'session_id'):
                self.get_or_create_view(SessionView, user_id).apply_event(event) 