from datetime import datetime
from uuid import uuid4
from behave.runner import Context
from cahoots_events.system_commands import CreateSystemUser
from cahoots_events.command_bus import CommandBus


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime"""
    return datetime.strptime(date_str, '%Y-%m-%d')


def ensure_agent_id(context: Context, agent_id: str) -> uuid4:
    """Ensure an agent ID exists in the context and return it"""
    if not hasattr(context, 'agent_ids'):
        context.agent_ids = {}
    if agent_id not in context.agent_ids:
        # Create a new UUID for the agent
        agent_uuid = uuid4()
        context.agent_ids[agent_id] = agent_uuid
        
        # Create the system user in our test environment
        command = CreateSystemUser(
            command_id=uuid4(),
            correlation_id=uuid4(),
            agent_id=agent_uuid,
            email=f"{agent_id}@example.com",
            name=agent_id.title()
        )
        CommandBus.handle(command)
        
    return context.agent_ids[agent_id]


def get_agent_id(context: Context, agent_id: str) -> uuid4:
    """Get an existing agent ID from the context"""
    if not hasattr(context, 'agent_ids') or agent_id not in context.agent_ids:
        raise ValueError(f"Agent {agent_id} does not exist")
    return context.agent_ids[agent_id]