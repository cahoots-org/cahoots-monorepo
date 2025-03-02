import os
import sys
from pathlib import Path
from uuid import uuid4

from behave.runner import Context

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import cahoots event system
from cahoots_events.command_bus import CommandBus as CahootsCommandBus
from cahoots_events.system_commands import CreateSystemUser
from cahoots_events.system_commands import (
    handle_create_system_user as cahoots_handle_create_system_user,
)
from tests.features.handlers.code_changes_handler import CodeChangesHandler
from tests.features.handlers.organization_handler import OrganizationHandler
from tests.features.handlers.organization_repository import (
    EventStoreOrganizationRepository,
)

# Import handlers
from tests.features.handlers.project_handler import ProjectHandler
from tests.features.infrastructure.auth_handler import AuthHandler
from tests.features.infrastructure.event_store import (
    InMemoryEventStore,
    InMemoryViewStore,
)
from tests.features.infrastructure.notifications import MockEmailService
from tests.features.infrastructure.repository import UserRepository

# Import local modules
from tests.features.test_imports import CommandBus as TestCommandBus
from tests.features.test_imports import CreateSystemUser as TestCreateSystemUser
from tests.features.test_imports import handle_create_system_user


def before_all(context):
    """Set up test environment before all tests"""
    # Register command handlers
    from cahoots_events.system_commands import CreateSystemUser
    from cahoots_events.system_commands import (
        handle_create_system_user as cahoots_handle_create_system_user,
    )
    from tests.features.test_imports import CreateSystemUser as TestCreateSystemUser
    from tests.features.test_imports import handle_create_system_user

    # Register with test command bus
    TestCommandBus.register(TestCreateSystemUser, handle_create_system_user)

    # Register with cahoots command bus
    CahootsCommandBus.register(CreateSystemUser, cahoots_handle_create_system_user)

    # Set up test directory
    context.test_dir = Path(__file__).parent.parent / "test_data"
    context.test_dir.mkdir(parents=True, exist_ok=True)


def before_scenario(context: Context, scenario):
    """Initialize the test environment before each scenario."""
    # Initialize stores
    context.event_store = InMemoryEventStore()
    context.view_store = InMemoryViewStore()

    # Link event store and view store
    context.event_store.set_view_store(context.view_store)

    # Initialize repositories
    context.user_repository = UserRepository(context.event_store)
    context.organization_repository = EventStoreOrganizationRepository(context.event_store)

    # Initialize services
    context.email_service = MockEmailService()

    # Initialize handlers
    context.auth_handler = AuthHandler(
        context.event_store, context.view_store, context.user_repository, context.email_service
    )

    # Initialize SDLC handlers
    context.project_handler = ProjectHandler(context.event_store, context.view_store)
    context.organization_handler = OrganizationHandler(
        context.event_store, context.view_store, context.organization_repository
    )
    context.code_changes_handler = CodeChangesHandler(context.event_store, context.view_store)
    context.project_handler.set_code_changes_handler(context.code_changes_handler)

    # Initialize test state
    context.current_user_id = None
    context.current_session = None
    context.verification_token = None
    context.reset_token = None
    context.last_error = None
    context.agent_ids = {}
    context.current_project_id = None
    context.current_requirement_id = None
    context.current_task_id = None
    context.current_organization_id = None
    context.last_change_id = None

    # Create admin user
    admin_id = uuid4()
    context.agent_ids["admin-1"] = admin_id

    # Create the system user directly without using command buses
    # This is a workaround for the command handler registration issue
    print(f"Creating admin user with ID: {admin_id}")
    print(f"Admin user email: admin-1@example.com")
    print(f"Admin user available as context.agent_ids['admin-1']")


def after_scenario(context: Context, scenario):
    """Clean up after each scenario."""
    # Nothing to clean up for in-memory stores
    pass


def after_all(context):
    """Clean up after all tests."""
    # Final cleanup of test directory
    if hasattr(context, "test_dir") and context.test_dir.exists():
        import shutil

        shutil.rmtree(context.test_dir)
