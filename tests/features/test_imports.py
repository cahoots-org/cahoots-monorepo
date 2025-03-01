"""
Test imports module that provides wrappers for external dependencies
to make test files easier to maintain.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4

# Event and Command classes for tests
class Event:
    """Base Event class for tests"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional['EventMetadata'] = None):
        self.event_id = event_id
        self.timestamp = timestamp
        self.metadata = metadata or EventMetadata()

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement aggregate_id")


class EventMetadata:
    """Metadata for event tracking and versioning"""
    def __init__(self, schema_version: int = 1, causation_id: Optional[UUID] = None,
                 correlation_id: Optional[UUID] = None, actor_id: Optional[UUID] = None):
        self.schema_version = schema_version
        self.causation_id = causation_id
        self.correlation_id = correlation_id or uuid4()
        self.created_at = datetime.utcnow()
        self.actor_id = actor_id
        self.context = {}


# User aggregate
class User:
    """User aggregate for authentication"""
    def __init__(self, user_id=None, email=None, name=None):
        self.user_id = user_id or uuid4()
        self.email = email
        self.name = name
        self.is_active = True
        self.pending_events = []
        self.password_hash = None
    
    def apply_event(self, event):
        """Apply an event to this user"""
        # Stub implementation for tests
        return
        

# Project events
class ProjectCreated(Event):
    """Event when a new project is created"""
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


# Code change events
class CodeChangeProposed(Event):
    """Event when a code change is proposed"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, change_id: UUID, files: List[str], description: str,
                 reasoning: str, proposed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.files = files
        self.description = description
        self.reasoning = reasoning
        self.proposed_by = proposed_by

    @property
    def aggregate_id(self) -> UUID:
        return self.project_id


class CodeChangeReviewed(Event):
    """Event when a code change is reviewed"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, change_id: UUID, status: str, comments: str,
                 suggested_changes: str, reviewed_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.status = status
        self.comments = comments
        self.suggested_changes = suggested_changes
        self.reviewed_by = reviewed_by

    @property
    def aggregate_id(self) -> UUID:
        return self.project_id


class CodeChangeImplemented(Event):
    """Event when a code change is implemented"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 project_id: UUID, change_id: UUID, implemented_by: UUID):
        super().__init__(event_id, timestamp, metadata)
        self.project_id = project_id
        self.change_id = change_id
        self.implemented_by = implemented_by

    @property
    def aggregate_id(self) -> UUID:
        return self.project_id


# Command bus for tests
class CommandBus:
    """Simple command bus for tests"""
    _handlers = {}

    @classmethod
    def register(cls, command_type, handler):
        """Register a command handler"""
        cls._handlers[command_type] = handler

    @classmethod
    def handle(cls, command):
        """Handle a command"""
        handler = cls._handlers.get(type(command))
        if handler is None:
            raise ValueError(f"No handler registered for {type(command)}")
        return handler(command)


# System commands
class CreateSystemUser:
    """Command to create a system user"""
    def __init__(self, command_id, correlation_id, agent_id, email, name):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.agent_id = agent_id
        self.email = email
        self.name = name


def handle_create_system_user(command):
    """Handle create system user command"""
    # This is a stub implementation for tests
    return [command.agent_id]


# Team Events
class TeamCreated:
    """Event for team creation"""
    def __init__(self, team_id, organization_id, name, description, created_by, metadata):
        self.team_id = team_id
        self.organization_id = organization_id
        self.name = name
        self.description = description
        self.created_by = created_by
        self.metadata = metadata
        
class TeamMemberAdded:
    """Event for adding a member to a team"""
    def __init__(self, team_id, user_id, role, added_by, metadata):
        self.team_id = team_id
        self.user_id = user_id
        self.role = role
        self.added_by = added_by
        self.metadata = metadata
        
class TeamMemberRoleUpdated:
    """Event for updating a team member's role"""
    def __init__(self, team_id, user_id, old_role, new_role, reason, updated_by, metadata):
        self.team_id = team_id
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role
        self.reason = reason
        self.updated_by = updated_by
        self.metadata = metadata
        
class TeamMemberRemoved:
    """Event for removing a member from a team"""
    def __init__(self, team_id, user_id, removed_by, metadata):
        self.team_id = team_id
        self.user_id = user_id
        self.removed_by = removed_by
        self.metadata = metadata
        
class TeamArchived:
    """Event for archiving a team"""
    def __init__(self, team_id, reason, archived_by, metadata):
        self.team_id = team_id
        self.reason = reason
        self.archived_by = archived_by
        self.metadata = metadata
        
class TeamLeadershipTransferred:
    """Event for transferring team leadership"""
    def __init__(self, team_id, old_lead_id, new_lead_id, metadata):
        self.team_id = team_id
        self.old_lead_id = old_lead_id
        self.new_lead_id = new_lead_id
        self.metadata = metadata 

# Authentication Commands
class RegisterUser:
    """Command to register a new user"""
    def __init__(self, command_id, correlation_id, email, password, name):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email
        self.password = password
        self.name = name

class VerifyEmail:
    """Command to verify a user's email"""
    def __init__(self, command_id, correlation_id, user_id, verification_token):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.verification_token = verification_token

class Login:
    """Command to log in a user"""
    def __init__(self, command_id, correlation_id, email, password, device_info=None):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email
        self.password = password
        self.device_info = device_info

class RequestPasswordReset:
    """Command to request a password reset"""
    def __init__(self, command_id, correlation_id, email):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.email = email

class ResetPassword:
    """Command to reset a user's password"""
    def __init__(self, command_id, correlation_id, user_id, reset_token, new_password):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.reset_token = reset_token
        self.new_password = new_password

class RefreshAccessToken:
    """Command to refresh an access token"""
    def __init__(self, command_id, correlation_id, user_id, refresh_token):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.refresh_token = refresh_token

class Logout:
    """Command to log out a user"""
    def __init__(self, command_id, correlation_id, user_id, session_id):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id

class RevokeSession:
    """Command to revoke a specific session"""
    def __init__(self, command_id, correlation_id, user_id, session_id):
        self.command_id = command_id
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id 