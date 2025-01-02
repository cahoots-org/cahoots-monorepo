"""Factory for creating agent instances."""
import os
import traceback
from typing import Optional, Type

from src.agents.base_agent import BaseAgent
from src.agents.developer import Developer
from src.agents.tester import Tester
from src.agents.ux_designer import UXDesigner
from src.agents.project_manager import ProjectManager
from src.utils.base_logger import BaseLogger
from src.utils.event_system import EventSystem

class AgentFactory:
    """Factory class for creating agent instances."""

    def __init__(self, logger: Optional[BaseLogger] = None) -> None:
        """Initialize the factory.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self._logger = logger or BaseLogger("AgentFactory")
        self._event_system = EventSystem()  # Create a single event system instance for all agents

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

            # Create PM agent
            if agent_type == "pm":
                trello_key = os.getenv("TRELLO_API_KEY")
                if not trello_key:
                    error_msg = "TRELLO_API_KEY environment variable is missing"
                    self._logger.error(error_msg)
                    raise RuntimeError(error_msg)

                trello_secret = os.getenv("TRELLO_API_SECRET")
                if not trello_secret:
                    error_msg = "TRELLO_API_SECRET environment variable is missing"
                    self._logger.error(error_msg)
                    raise RuntimeError(error_msg)

                return ProjectManager(event_system=self._event_system)

            # Create developer agent
            elif agent_type == "developer":
                if not os.getenv("DEVELOPER_ID"):
                    error_msg = "DEVELOPER_ID environment variable must be set for developer agents"
                    self._logger.error(error_msg)
                    raise ValueError(error_msg)

                return Developer(os.getenv("DEVELOPER_ID"), event_system=self._event_system)

            # Create UX designer agent
            elif agent_type == "ux":
                if not os.getenv("DESIGNER_ID"):
                    error_msg = "DESIGNER_ID environment variable must be set for UX designer"
                    self._logger.error(error_msg)
                    raise ValueError(error_msg)

                return UXDesigner(event_system=self._event_system)

            # Create tester agent
            elif agent_type == "tester":
                if not os.getenv("TESTER_ID"):
                    error_msg = "TESTER_ID environment variable must be set for tester"
                    self._logger.error(error_msg)
                    raise ValueError(error_msg)

                return Tester(event_system=self._event_system)

            # Handle unknown agent type
            else:
                error_msg = f"Unknown agent type: {agent_type}"
                self._logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            self._logger.error(f"Failed to create agent: {str(e)}")
            self._logger.error("Stack trace:\n" + traceback.format_exc())
            raise

async def main() -> None:
    """Main entry point for the factory module."""
    factory = AgentFactory()
    try:
        agent = factory.create_agent()
        await agent.run()
    except Exception as e:
        factory._logger.error(f"Error in main: {str(e)}")
        factory._logger.error("Stack trace:\n" + traceback.format_exc())
        raise 