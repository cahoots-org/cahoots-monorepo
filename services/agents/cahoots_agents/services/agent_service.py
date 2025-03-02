"""Service entrypoint for running agents."""

import asyncio
import logging
import os
from typing import Optional

from cahoots_core.config import Config
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus import EventSystem

from ..factory import AgentFactory

logger = logging.getLogger(__name__)


async def run_agent(
    agent_type: str,
    event_system: Optional[EventSystem] = None,
    github_service: Optional[GitHubService] = None,
    config: Optional[Config] = None,
) -> None:
    """Run an agent service.

    Args:
        agent_type: Type of agent to run
        event_system: Optional event system
        github_service: Optional GitHub service
        config: Optional configuration
    """
    try:
        # Create and start agent
        agent = AgentFactory.create(
            agent_type=agent_type,
            event_system=event_system,
            github_service=github_service,
            config=config,
        )

        # Start agent and wait forever
        await agent.start()
        await asyncio.Event().wait()  # Run indefinitely

    except Exception as e:
        logger.error(f"Error running {agent_type} agent: {str(e)}")
        raise


def main() -> None:
    """Main entry point."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Get agent type from environment
    agent_type = os.getenv("AGENT_TYPE")
    if not agent_type:
        raise ValueError("AGENT_TYPE environment variable must be set")

    # Create event system
    event_system = EventSystem()

    # Create GitHub service
    github_service = GitHubService()

    # Load config
    config = Config.from_env()

    # Run agent
    asyncio.run(
        run_agent(
            agent_type=agent_type,
            event_system=event_system,
            github_service=github_service,
            config=config,
        )
    )


if __name__ == "__main__":
    main()
