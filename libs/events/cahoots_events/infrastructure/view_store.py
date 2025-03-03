"""View store implementation"""

from typing import Dict, Generic, Optional, Type, TypeVar
from uuid import UUID

from ..auth.views import SessionView, UserView
from ..code_changes.views import CodeChangeView
from ..organization.views import OrganizationView
from ..project.views import ProjectOverviewView, RequirementsView, TaskBoardView
from ..team.views import TeamView

T = TypeVar("T")


class ViewCollection(Generic[T]):
    """Generic collection for managing views of a specific type"""

    def __init__(self):
        self.views: Dict[UUID, T] = {}

    def get(self, entity_id: UUID) -> Optional[T]:
        """Get view by entity ID"""
        return self.views.get(entity_id)

    def add(self, entity_id: UUID, view: T) -> T:
        """Add or update view"""
        self.views[entity_id] = view
        return view


class InMemoryViewStore:
    """In-memory implementation of view store"""

    def __init__(self):
        # Authentication views
        self.user_views = ViewCollection[UserView]()
        self.session_views = ViewCollection[SessionView]()

        # Organization views
        self.organization_views = ViewCollection[OrganizationView]()

        # Team views
        self.team_views = ViewCollection[TeamView]()

        # Project views
        self.project_views = ViewCollection[ProjectOverviewView]()
        self.requirements_views = ViewCollection[RequirementsView]()
        self.task_board_views = ViewCollection[TaskBoardView]()

        # Code change views
        self.code_change_views = ViewCollection[CodeChangeView]()

    def create_view(self, view_type: Type[T], entity_id: UUID, **kwargs) -> T:
        """Create a new view instance"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            raise ValueError(f"Unknown view type: {view_type}")

        if view_type == UserView:
            view = UserView(user_id=entity_id, **kwargs)
        elif view_type == SessionView:
            view = SessionView(user_id=entity_id, **kwargs)
        elif view_type == OrganizationView:
            view = OrganizationView(organization_id=entity_id, **kwargs)
        elif view_type == TeamView:
            view = TeamView(team_id=entity_id, **kwargs)
        elif view_type == ProjectOverviewView:
            view = ProjectOverviewView(project_id=entity_id, **kwargs)
        elif view_type == RequirementsView:
            view = RequirementsView(project_id=entity_id, **kwargs)
        elif view_type == TaskBoardView:
            view = TaskBoardView(project_id=entity_id, **kwargs)
        elif view_type == CodeChangeView:
            view = CodeChangeView(project_id=entity_id, **kwargs)
        else:
            raise ValueError(f"Unknown view type: {view_type}")

        return view_collection.add(entity_id, view)

    def get_or_create_view(self, view_type: Type[T], entity_id: UUID, **kwargs) -> T:
        """Get existing view or create new one"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            raise ValueError(f"Unknown view type: {view_type}")

        view = view_collection.get(entity_id)
        if view is None:
            view = self.create_view(view_type, entity_id, **kwargs)
        return view

    def get_view(self, entity_id: UUID, view_type: Type[T]) -> Optional[T]:
        """Get view by type and entity ID"""
        view_collection = self._get_collection_for_type(view_type)
        if view_collection is None:
            return None
        return view_collection.get(entity_id)

    def _get_collection_for_type(self, view_type: Type[T]) -> Optional[ViewCollection[T]]:
        """Get the appropriate view collection for a view type"""
        if view_type == UserView:
            return self.user_views
        elif view_type == SessionView:
            return self.session_views
        elif view_type == OrganizationView:
            return self.organization_views
        elif view_type == TeamView:
            return self.team_views
        elif view_type == ProjectOverviewView:
            return self.project_views
        elif view_type == RequirementsView:
            return self.requirements_views
        elif view_type == TaskBoardView:
            return self.task_board_views
        elif view_type == CodeChangeView:
            return self.code_change_views
        return None

    def apply_event(self, event):
        """Apply an event to all relevant views"""
        # Get entity ID and relevant view types based on event type
        if hasattr(event, "user_id"):
            self.get_or_create_view(UserView, event.user_id).apply_event(event)
            if hasattr(event, "session_id"):
                self.get_or_create_view(SessionView, event.user_id).apply_event(event)

        if hasattr(event, "organization_id"):
            self.get_or_create_view(OrganizationView, event.organization_id).apply_event(event)

        if hasattr(event, "team_id"):
            self.get_or_create_view(TeamView, event.team_id).apply_event(event)

        if hasattr(event, "project_id"):
            self.get_or_create_view(ProjectOverviewView, event.project_id).apply_event(event)
            self.get_or_create_view(RequirementsView, event.project_id).apply_event(event)
            self.get_or_create_view(TaskBoardView, event.project_id).apply_event(event)
            if hasattr(event, "change_id"):
                self.get_or_create_view(CodeChangeView, event.project_id).apply_event(event)

    def save_view(self, view_id: UUID, view: T) -> None:
        """Save a view to the store"""
        view_type = type(view)
        key = f"{view_type.__name__}:{view_id}"
        self._views[key] = view

    def get_all_views(self, view_type: Type[T]) -> Dict[UUID, T]:
        """Get all views of a specific type"""
        prefix = f"{view_type.__name__}:"
        result = {}
        for key, view in self._views.items():
            if key.startswith(prefix):
                view_id = key[len(prefix) :]
                result[view_id] = view
        return result
