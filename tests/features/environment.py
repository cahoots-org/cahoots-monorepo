from behave.runner import Context
from pathlib import Path
from uuid import uuid4

from cahoots_events.command_bus import CommandBus
from cahoots_events.system_commands import CreateSystemUser, handle_create_system_user
from features.infrastructure.event_store import InMemoryEventStore, InMemoryViewStore
from features.infrastructure.repository import UserRepository
from features.infrastructure.notifications import MockEmailService
from features.infrastructure.auth_handler import AuthHandler


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
    context.user_repository = UserRepository(context.event_store)
    
    # Initialize services
    context.email_service = MockEmailService()
    
    # Initialize handlers
    context.auth_handler = AuthHandler(
        context.event_store,
        context.view_store,
        context.user_repository,
        context.email_service
    )
    
    # Initialize test state
    context.current_user_id = None
    context.current_session = None
    context.verification_token = None
    context.reset_token = None
    context.last_error = None
    context.agent_ids = {}

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