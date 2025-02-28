from behave.runner import Context
from pathlib import Path
from uuid import uuid4

from sdlc.application.handlers import ProjectHandler
from sdlc.application.organization_handler import OrganizationHandler
from sdlc.domain.auth.handler import AuthHandler
from sdlc.domain.auth.repository import EventStoreUserRepository
from sdlc.domain.auth.notifications import MockEmailService
from sdlc.domain.code_changes.handler import CodeChangesHandler
from sdlc.domain.organization.repository import EventStoreOrganizationRepository
from sdlc.infrastructure.view_store import InMemoryViewStore
from domain.commands.command_bus import CommandBus
from domain.commands.create_system_user import CreateSystemUser, handle_create_system_user
from sdlc.domain.organization.commands import (
    CreateOrganization, UpdateOrganizationName,
    AddOrganizationMember, RemoveOrganizationMember,
    ChangeOrganizationMemberRole, ArchiveOrganization
)
from tests.features.steps.event_store_steps import InMemoryEventStore


def before_all(context):
    """Set up test environment before all tests"""
    # Register command handlers
    CommandBus.register(CreateSystemUser, handle_create_system_user)
    
    # Set up test directory
    context.test_dir = Path(__file__).parent.parent / 'test_data'
    context.test_dir.mkdir(parents=True, exist_ok=True)


def before_scenario(context: Context, scenario):
    """Initialize the test environment before each scenario."""
    # Initialize stores
    context.event_store = InMemoryEventStore()
    context.view_store = InMemoryViewStore()
    
    # Initialize repositories
    context.organization_repository = EventStoreOrganizationRepository(context.event_store)
    context.user_repository = EventStoreUserRepository(context.event_store)
    
    # Initialize services
    context.email_service = MockEmailService()
    
    # Initialize handlers
    context.project_handler = ProjectHandler(context.event_store, context.view_store)
    context.organization_handler = OrganizationHandler(
        context.event_store,
        context.view_store,
        context.organization_repository
    )
    context.auth_handler = AuthHandler(
        context.event_store,
        context.view_store,
        context.user_repository,
        context.email_service
    )
    context.code_changes_handler = CodeChangesHandler(context.event_store, context.view_store)
    context.project_handler.set_code_changes_handler(context.code_changes_handler)
    
    # Initialize test state
    context.current_project_id = None
    context.current_requirement_id = None
    context.current_task_id = None
    context.current_organization_id = None
    context.agent_ids = {}
    context.last_change_id = None
    context.last_error = None

    # Create admin user
    admin_id = uuid4()
    context.agent_ids['admin-1'] = admin_id
    cmd = CreateSystemUser(
        command_id=uuid4(),
        correlation_id=uuid4(),
        agent_id=admin_id,
        email="admin-1@example.com",
        name="Admin One"
    )
    CommandBus.handle(cmd)


def after_scenario(context: Context, scenario):
    """Clean up after each scenario."""
    # Nothing to clean up for in-memory stores
    pass


def after_all(context):
    """Clean up after all tests."""
    # Final cleanup of test directory
    if hasattr(context, 'test_dir') and context.test_dir.exists():
        import shutil
        shutil.rmtree(context.test_dir) 