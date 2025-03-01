"""Project management domain repositories"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .aggregates import Project
from .events import ProjectCreated


class ProjectRepository(ABC):
    """Abstract base class for project repositories"""

    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID"""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Project]:
        """Get project by name"""
        pass

    @abstractmethod
    def save(self, project: Project) -> None:
        """Save project aggregate"""
        pass


class EventStoreProjectRepository(ProjectRepository):
    """Event store implementation of project repository"""

    def __init__(self, event_store):
        self.event_store = event_store

    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID"""
        events = self.event_store.get_events_for_aggregate(project_id)
        if not events:
            return None

        project = Project(project_id=project_id)
        for event in events:
            project.apply_event(event)
        return project

    def get_by_name(self, name: str) -> Optional[Project]:
        """Get project by name"""
        # Get all project creation events
        events = self.event_store.get_all_events()
        creation_event = next(
            (e for e in events 
             if isinstance(e, ProjectCreated) and e.name == name),
            None
        )
        if not creation_event:
            return None

        return self.get_by_id(creation_event.project_id)

    def save(self, project: Project) -> None:
        """Save project aggregate - no-op for event store"""
        # No need to save the aggregate since we're using event sourcing
        pass 