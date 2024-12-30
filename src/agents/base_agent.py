# src/agents/base_agent.py
from abc import ABC, abstractmethod
from ..utils.logger import Logger
from ..utils.event_system import EventSystem
from ..utils.model import Model
import asyncio

class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, model_name: str):
        """Initialize the base agent with modern model and proper setup."""
        try:
            self.logger = Logger(self.__class__.__name__)
            self.logger.debug(f"Initializing {self.__class__.__name__} with model {model_name}")
            
            self.model_name = model_name
            self.logger.debug("Creating event system")
            self.event_system = EventSystem()
            
            self.logger.debug(f"Initializing {model_name} model")
            self.model = Model(model_name)
            
            self.logger.info(f"{self.__class__.__name__} base initialization complete")
        except Exception as e:
            # Log the error before re-raising to ensure it's captured
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
                self.logger.error("Stack trace:", exc_info=True)
            raise
        
    @abstractmethod
    async def setup_events(self):
        """Initialize event system and subscribe to channels.
        Each agent must implement this to set up their specific event subscriptions."""
        
    def generate_response(self, prompt: str) -> str:
        """Generate a response using the AI model.
        
        Args:
            prompt: The input prompt to generate a response for.
            
        Returns:
            str: The generated response.
            
        Raises:
            Exception: If there is an error generating the response.
        """
        return self.model.generate_response(prompt)
        
    async def handle_system_message(self, message: dict):
        """Handle system-wide messages."""
        self.logger.info(f"Received system message: {message}")
        # Implement system message handling