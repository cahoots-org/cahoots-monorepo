from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..events import Event, EventMetadata


@dataclass
class CodeChangeProposed(Event):
    project_id: UUID
    change_id: UUID
    files: List[str]
    description: str
    reasoning: str
    proposed_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        project_id: UUID,
        change_id: UUID,
        files: List[str],
        description: str,
        reasoning: str,
        proposed_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.files = files
        self.description = description
        self.reasoning = reasoning
        self.proposed_by = proposed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class CodeChangeReviewed(Event):
    project_id: UUID
    change_id: UUID
    status: str
    comments: str
    suggested_changes: str
    reviewed_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        project_id: UUID,
        change_id: UUID,
        status: str,
        comments: str,
        suggested_changes: str,
        reviewed_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.status = status
        self.comments = comments
        self.suggested_changes = suggested_changes
        self.reviewed_by = reviewed_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id


@dataclass
class CodeChangeImplemented(Event):
    project_id: UUID
    change_id: UUID
    implemented_by: UUID

    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        metadata: Optional[EventMetadata],
        project_id: UUID,
        change_id: UUID,
        implemented_by: UUID,
    ):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.implemented_by = implemented_by

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.project_id
