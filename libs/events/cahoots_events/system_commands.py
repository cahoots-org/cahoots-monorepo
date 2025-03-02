"""System command definitions"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateSystemUser:
    """Command to create a system user"""

    command_id: UUID
    correlation_id: UUID
    agent_id: UUID
    email: str
    name: str


# Handler for CreateSystemUser command
def handle_create_system_user(command: CreateSystemUser) -> None:
    """Handle creating a system user (mock implementation for tests)"""
    # This is a mock implementation that doesn't need to do anything
    # In a real system, this would create the user in a database
    pass
