from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class EventMetadata:
    """Metadata for event tracking and versioning"""
    schema_version: int = 1  # Schema version for event structure
    causation_id: Optional[UUID] = None  # ID of the event that caused this event
    correlation_id: Optional[UUID] = None  # ID linking related events
    created_at: datetime = field(default_factory=datetime.utcnow)  # When the event was created
    actor_id: Optional[UUID] = None  # ID of the actor who triggered this event
    context: Dict = field(default_factory=dict)  # Additional context about the event

    def __post_init__(self):
        """Initialize correlation_id if not provided"""
        if self.correlation_id is None:
            self.correlation_id = uuid4()


class Event(ABC):
    """Abstract base class for all events"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata] = None):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata or EventMetadata()
        self.validate()

    def validate(self):
        """Base validation method that can be extended by specific event types"""
        if not isinstance(self.event_id, UUID):
            raise ValueError("event_id must be a UUID")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")

    def with_context(self, **kwargs) -> 'Event':
        """Add context to the event"""
        self.metadata.context.update(kwargs)
        return self

    def caused_by(self, event: 'Event') -> 'Event':
        """Set the causation ID from another event"""
        self.metadata.causation_id = event.event_id
        self.metadata.correlation_id = event.metadata.correlation_id
        return self

    def triggered_by(self, actor_id: UUID) -> 'Event':
        """Set the actor who triggered this event"""
        self.metadata.actor_id = actor_id
        return self

    @property
    def version(self) -> int:
        """Get the schema version of this event"""
        return self.metadata.schema_version

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement aggregate_id")


@dataclass
class OrganizationCreated(Event):
    """Event when a new organization is created"""
    organization_id: UUID
    name: str
    description: str
    created_by: UUID

    def validate(self):
        """Example of extended validation for specific event type"""
        super().validate()
        if not isinstance(self.organization_id, UUID):
            raise ValueError("organization_id must be a UUID")
        if not isinstance(self.created_by, UUID):
            raise ValueError("created_by must be a UUID")
        if not self.name.strip():
            raise ValueError("name cannot be empty")

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self.organization_id


@dataclass
class OrganizationNameUpdated(Event):
    """Event when an organization's name is updated"""
    organization_id: UUID
    old_name: str
    new_name: str
    updated_by: UUID


@dataclass
class OrganizationMemberAdded(Event):
    """Event when a member is added to an organization"""
    organization_id: UUID
    member_id: UUID
    role: str
    added_by: UUID


@dataclass
class OrganizationMemberRemoved(Event):
    """Event when a member is removed from an organization"""
    organization_id: UUID
    member_id: UUID
    removed_by: UUID
    reason: Optional[str] = None


@dataclass
class TeamCreated(Event):
    """Event when a new team is created"""
    organization_id: UUID
    team_id: UUID
    name: str
    description: str
    created_by: UUID

    def validate(self):
        """Validate team creation event"""
        super().validate()
        if not isinstance(self.organization_id, UUID):
            raise ValueError("organization_id must be a UUID")
        if not isinstance(self.team_id, UUID):
            raise ValueError("team_id must be a UUID")
        if not isinstance(self.created_by, UUID):
            raise ValueError("created_by must be a UUID")
        if not self.name.strip():
            raise ValueError("name cannot be empty")


@dataclass
class TeamMemberAdded(Event):
    """Event when a member is added to a team"""
    team_id: UUID
    member_id: UUID
    role: str
    added_by: UUID

    def validate(self):
        """Validate team member addition event"""
        super().validate()
        if not isinstance(self.team_id, UUID):
            raise ValueError("team_id must be a UUID")
        if not isinstance(self.member_id, UUID):
            raise ValueError("member_id must be a UUID")
        if not isinstance(self.added_by, UUID):
            raise ValueError("added_by must be a UUID")
        if not self.role.strip():
            raise ValueError("role cannot be empty")
        if self.role not in {'lead', 'member', 'developer', 'senior'}:
            raise ValueError(f"Invalid role: {self.role}")


@dataclass
class TeamMemberRemoved(Event):
    """Event when a member is removed from a team"""
    team_id: UUID
    member_id: UUID
    removed_by: UUID

    def validate(self):
        """Validate member removal event"""
        super().validate()
        if not isinstance(self.team_id, UUID):
            raise ValueError("team_id must be a UUID")
        if not isinstance(self.member_id, UUID):
            raise ValueError("member_id must be a UUID")
        if not isinstance(self.removed_by, UUID):
            raise ValueError("removed_by must be a UUID")


@dataclass
class TeamMemberRoleChanged(Event):
    """Event when a team member's role is changed"""
    team_id: UUID
    member_id: UUID
    new_role: str
    reason: str
    updated_by: UUID

    def validate(self):
        """Validate role change event"""
        super().validate()
        if not isinstance(self.team_id, UUID):
            raise ValueError("team_id must be a UUID")
        if not isinstance(self.member_id, UUID):
            raise ValueError("member_id must be a UUID")
        if not isinstance(self.updated_by, UUID):
            raise ValueError("updated_by must be a UUID")
        if not self.new_role.strip():
            raise ValueError("new_role cannot be empty")
        if not self.reason.strip():
            raise ValueError("reason cannot be empty")
        if self.new_role not in {'lead', 'member', 'developer', 'senior'}:
            raise ValueError(f"Invalid role: {self.new_role}")


@dataclass
class TeamArchived(Event):
    """Event when a team is archived"""
    team_id: UUID
    archived_by: UUID
    reason: str
    organization_id: Optional[UUID] = None


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


@dataclass
class CodeChangeProposed(Event):
    project_id: UUID
    task_id: UUID
    change_id: UUID
    files: List[str]
    description: str
    proposed_by: UUID
    diff: str
    reasoning: str


@dataclass
class CodeChangeReviewed(Event):
    project_id: UUID
    change_id: UUID
    reviewer_id: UUID
    status: str  # 'approved', 'rejected', 'changes_requested'
    comments: List[Dict]
    suggested_changes: Dict


@dataclass
class CodeChangeImplemented(Event):
    project_id: UUID
    change_id: UUID
    implemented_by: UUID
    final_diff: str
    affected_files: List[str]


@dataclass
class TestResultRecorded(Event):
    project_id: UUID
    test_id: UUID
    change_id: UUID
    result: str  # 'passed', 'failed'
    coverage: float
    failures: List[Dict]


@dataclass
class TeamLeadershipTransferred(Event):
    """Event when team leadership is transferred"""
    team_id: UUID
    new_lead_id: UUID
    transferred_by: UUID

    def validate(self):
        """Validate leadership transfer event"""
        super().validate()
        if not isinstance(self.team_id, UUID):
            raise ValueError("team_id must be a UUID")
        if not isinstance(self.new_lead_id, UUID):
            raise ValueError("new_lead_id must be a UUID")
        if not isinstance(self.transferred_by, UUID):
            raise ValueError("transferred_by must be a UUID")
        if self.new_lead_id == self.transferred_by:
            raise ValueError("Cannot transfer leadership to self") 