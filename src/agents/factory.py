from typing import Optional
import os
import asyncio
import logging
import traceback
from .project_manager import ProjectManager
from .developer import Developer
from .ux_designer import UXDesigner
from .tester import Tester
from ..utils.logger import Logger

# Configure logging using dictConfig
from logging.config import dictConfig

log_level = 'DEBUG'  # Force debug level for now
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': log_level,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'handlers': ['default'],
        'level': log_level,
    },
}

dictConfig(logging_config)

class AgentFactory:
    """Factory for creating and running different types of agents."""
    
    @staticmethod
    def create_agent(agent_type: Optional[str] = None):
        """Create an agent based on type or environment variable."""
        logger = Logger("AgentFactory")
        
        try:
            # Get agent type from environment if not provided
            agent_type = agent_type or os.getenv("AGENT_TYPE")
            if not agent_type:
                logger.error("AGENT_TYPE environment variable must be set")
                raise ValueError("AGENT_TYPE environment variable must be set")
                
            agent_type = agent_type.lower()
            logger.info(f"Creating agent of type: {agent_type}")
            
            # Validate environment variables before creating agents
            if agent_type == "pm":
                logger.debug("Validating PM environment variables")
                if not os.getenv("TRELLO_API_KEY"):
                    logger.error("TRELLO_API_KEY environment variable is missing")
                    raise RuntimeError("TRELLO_API_KEY environment variable is missing")
                if not os.getenv("TRELLO_API_SECRET"):
                    logger.error("TRELLO_API_SECRET environment variable is missing")
                    raise RuntimeError("TRELLO_API_SECRET environment variable is missing")
                logger.debug("PM environment variables validated")
                return ProjectManager()
            elif agent_type == "developer":
                logger.debug("Validating developer environment variables")
                developer_id = os.getenv("DEVELOPER_ID")
                if not developer_id:
                    logger.error("DEVELOPER_ID environment variable must be set for developer agents")
                    raise ValueError("DEVELOPER_ID environment variable must be set for developer agents")
                logger.debug("Developer environment variables validated")
                return Developer(developer_id)
            elif agent_type == "ux":
                logger.debug("Validating UX designer environment variables")
                if not os.getenv("DESIGNER_ID"):
                    logger.error("DESIGNER_ID environment variable must be set for UX designer")
                    raise ValueError("DESIGNER_ID environment variable must be set for UX designer")
                logger.debug("UX designer environment variables validated")
                return UXDesigner()
            elif agent_type == "tester":
                logger.debug("Validating tester environment variables")
                if not os.getenv("TESTER_ID"):
                    logger.error("TESTER_ID environment variable must be set for tester")
                    raise ValueError("TESTER_ID environment variable must be set for tester")
                logger.debug("Tester environment variables validated")
                return Tester()
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                raise ValueError(f"Unknown agent type: {agent_type}")
        except Exception as e:
            logger.error(f"Failed to create agent of type {agent_type}: {str(e)}")
            logger.error(f"Stack trace:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise

async def main():
    """Create and run the agent."""
    try:
        # Create and run the agent
        agent = AgentFactory.create_agent()
        print("Agent created successfully")
        
        # Set up events
        print("Setting up events")
        await agent.setup_events()
        print("Events set up successfully")
        
        # Keep the agent running
        print("Starting agent loop")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Error running agent: {str(e)}")
        print(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
        raise

# This ensures main() is called when the module is run directly
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
        raise 