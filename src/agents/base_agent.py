# src/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Union
import json
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
        
    async def start_listening(self):
        """Start listening for messages on subscribed channels."""
        if not self.event_system.pubsub:
            self.logger.error("No pubsub client available. Did you call setup_events()?")
            return
            
        try:
            self.logger.info("Starting message listener")
            async for message in self.event_system.pubsub.listen():
                if message["type"] == "message":
                    try:
                        channel = message["channel"].decode()
                        data = json.loads(message["data"].decode())
                        handler = self.event_system.handlers.get(channel)
                        if handler:
                            await handler(data)
                        else:
                            self.logger.warning(f"No handler for channel {channel}")
                    except Exception as e:
                        self.logger.error(f"Error processing message: {str(e)}")
                        self.logger.error("Stack trace:", exc_info=True)
        except Exception as e:
            self.logger.error(f"Listener loop error: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
            
    async def generate_response(self, prompt: str) -> str:
        """Generate a response using the AI model.
        
        Args:
            prompt: The input prompt to generate a response for.
            
        Returns:
            str: The generated response.
            
        Raises:
            Exception: If there is an error generating the response.
        """
        return await self.model.generate_response(prompt)
        
    async def handle_system_message(self, message: dict):
        """Handle system-wide messages."""
        self.logger.info(f"Received system message: {message}")
        # Implement system message handling
        
    async def process_message(self, message: Union[str, dict]) -> Dict[str, Any]:
        """Base message processing method.
        
        Args:
            message: The message to process. Can be either a JSON string or a dictionary.
            
        Returns:
            Dict[str, Any]: The response to the message.
            
        Raises:
            ValueError: If the message is invalid or missing required fields.
        """
        try:
            # Convert string message to dict if needed
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode message as JSON: {str(e)}")
                    raise ValueError(f"Invalid JSON message: {str(e)}")
            
            if "type" not in message:
                self.logger.error(f"Message missing 'type' field: {message}")
                raise ValueError(f"Message missing required field 'type': {message}")
                
            self.logger.info(f"Processing message type: {message['type']}")
            return await self._handle_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
            
    @abstractmethod
    async def _handle_message(self, message: dict) -> Dict[str, Any]:
        """Handle a specific message type. Must be implemented by subclasses.
        
        Args:
            message: The message to handle, already decoded if it was a string.
            
        Returns:
            Dict[str, Any]: The response to the message.
        """
        pass