"""Command for creating system users"""
from dataclasses import dataclass
from uuid import UUID

from .command_bus import Command


@dataclass
class CreateSystemUser(Command):
    """Command to create a system user"""
    agent_id: UUID
    email: str
    name: str


def handle_create_system_user(command: CreateSystemUser) -> None:
    """Handle the CreateSystemUser command"""
    # In a real implementation, this would create the user in a database
    # For now, we'll just pass since we only need the agent_id for testing
    pass


# Register the handler
from .command_bus import CommandBus
CommandBus.register(CreateSystemUser, handle_create_system_user) 