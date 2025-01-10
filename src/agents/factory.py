"""Factory for creating agent instances."""
import os
import traceback
from typing import Optional, Dict, Callable, Any

from src.agents.base_agent import BaseAgent
from src.agents.developer import Developer
from src.agents.qa_tester import QATester
from src.agents.ux_designer import UXDesigner
from src.agents.project_manager import ProjectManager
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger
from src.utils.model import Model
from src.services.github_service import GitHubService

class AgentFactory:
    """Factory for creating agent instances."""

    def __init__(self, event_system: Optional[EventSystem] = None,
                 model: Optional[Model] = None,
                 logger: Optional[BaseLogger] = None,
                 github_service: Optional[GitHubService] = None,
                 github_config: Optional[Any] = None):
        """Initialize the factory.

        Args:
            event_system: Optional event system instance
            model: Optional model instance
            logger: Optional logger instance
            github_service: Optional GitHub service instance for testing
            github_config: Optional GitHub config for testing
        """
        self._event_system = event_system or EventSystem()
        self._model = model
        self._logger = logger or BaseLogger("AgentFactory")
        self._github_service = github_service
        self._github_config = github_config

    def create_agent(self, agent_type: Optional[str] = None) -> BaseAgent:
        """Create an agent instance based on type.

        Args:
            agent_type: Optional agent type override. If not provided, uses ENV_AGENT_TYPE.

        Returns:
            The created agent instance

        Raises:
            ValueError: If agent type is invalid or required environment variables are missing
            RuntimeError: If agent creation fails
        """
        try:
            # Get agent type from args or environment
            agent_type = agent_type or os.getenv("AGENT_TYPE")
            if not agent_type:
                error_msg = "AGENT_TYPE environment variable must be set"
                self._logger.error(error_msg)
                raise ValueError(error_msg)

            agent_type = agent_type.lower()
            self._logger.info(f"Creating agent of type: {agent_type}")

            # Map agent types to their classes
            agent_map = {
                "developer": lambda: Developer(
                    "dev-1",
                    focus="backend",
                    event_system=self._event_system,
                    start_listening=False,  # Don't start listening immediately in tests
                    github_service=self._github_service,
                    github_config=self._github_config
                ),
                "qa_tester": lambda: QATester(
                    event_system=self._event_system,
                    start_listening=False
                ),
                "ux_designer": lambda: UXDesigner(
                    event_system=self._event_system,
                    start_listening=False,
                    github_service=self._github_service,
                    github_config=self._github_config
                ),
                "project_manager": lambda: ProjectManager(
                    event_system=self._event_system,
                    start_listening=False,
                    github_service=self._github_service,
                    github_config=self._github_config
                )
            }

            if agent_type not in agent_map:
                error_msg = f"Invalid agent type: {agent_type}. Must be one of: {list(agent_map.keys())}"
                self._logger.error(error_msg)
                raise ValueError(error_msg)

            # Create and return the agent instance
            return agent_map[agent_type]()

        except Exception as e:
            error_msg = f"Failed to create agent: {str(e)}\n{traceback.format_exc()}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

async def main():
    """Create and run an agent based on AGENT_TYPE environment variable."""
    factory = AgentFactory()
    agent = factory.create_agent()
    
    try:
        await agent.start()
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 