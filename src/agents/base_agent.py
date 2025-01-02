# src/agents/base_agent.py
from typing import Dict, Any, Optional, Coroutine
import logging
import traceback
import asyncio
from unittest.mock import AsyncMock

from src.utils.event_system import EventSystem
from src.utils.model import Model
from src.utils.base_logger import BaseLogger
from src.api.core import get_event_system
from src.utils.task_manager import TaskManager
from src.core.messaging import (
    validate_story_assignment,
    validate_message_type,
    create_success_response,
    create_error_response
)

class BaseAgent:
    """Base agent class with shared functionality."""
    
    def __init__(self, model_name: str, start_listening: bool = True, event_system: Optional[EventSystem] = None):
        """Initialize base agent.
        
        Args:
            model_name: Name of the model to use
            start_listening: Whether to start listening for events immediately
            event_system: Optional event system instance. If not provided, will get from singleton.
            
        Raises:
            Exception: If initialization fails for any reason
        """
        self.logger = BaseLogger(self.__class__.__name__)
        
        try:
            self.logger.debug(f"Initializing {self.__class__.__name__} with model {model_name}")
            
            # Set up event system
            self.logger.debug("Getting shared event system")
            self.event_system = event_system or get_event_system()
            
            # Set up model
            self.logger.debug(f"Initializing {model_name} model")
            self.model_name = model_name
            self.model = Model(model_name)
            
            # Set up task manager
            self._task_manager = TaskManager(self.__class__.__name__)
            self.task_manager = self._task_manager  # Public access for testing
            self._listening = False
            
            if start_listening:
                self._task_manager.create_task(self.start_listening())
                
            self.logger.info(f"{self.__class__.__name__} base initialization complete")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
    
    async def setup_events(self) -> None:
        """Initialize event system and subscribe to channels.
        
        This should be overridden by subclasses to set up their specific event subscriptions.
        """
        if not self.event_system.is_connected():
            await self.event_system.connect()
            
        # Subscribe to system messages by default
        await self.event_system.subscribe("system", self.handle_system_message)
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
    
    async def start_listening(self) -> None:
        """Start listening for events."""
        if self._listening:
            return
            
        self._task_manager.running = True
        self._listening = True
        self.logger.info("Starting event listener")
        
        try:
            while self._task_manager.running and self._listening:
                try:
                    message = await self.event_system.get_message()
                    if message:
                        await self._handle_message(message)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error handling message: {str(e)}")
                await asyncio.sleep(0.1)  # Prevent tight loop
        except asyncio.CancelledError:
            self.logger.info("Event listener cancelled")
        except Exception as e:
            self.logger.error(f"Error in event listener: {str(e)}")
        finally:
            self._listening = False
            self._task_manager.running = False
    
    async def stop_listening(self) -> None:
        """Stop listening for events."""
        self.logger.info("Stopping event listener")
        self._listening = False
        await self._task_manager.cancel_all()
        if self.event_system.is_connected():
            await self.event_system.disconnect()
    
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle
            
        Returns:
            Dict[str, Any]: The response to the message
            
        Raises:
            ValueError: If the message has an unknown type
        """
        raise NotImplementedError("Subclasses must implement _handle_message")
    
    async def generate_response(self, prompt: str) -> str:
        """Generate a response using the model.
        
        Args:
            prompt: The prompt to generate a response for
            
        Returns:
            str: The generated response
        """
        return await self.model.generate_response(prompt)
    
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: The system message to handle
        """
        self.logger.info(f"Received system message: {message}")
        # Subclasses can override this to handle system messages
        pass
    
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment message.
        
        Args:
            message: Story assignment message
            
        Returns:
            Dict[str, Any]: Response indicating success/failure
        """
        self.logger.info(f"Received story assignment: {message}")
        
        # Validate story assignment
        error = validate_story_assignment(message, getattr(self, f"{self.__class__.__name__.lower()}_id"), self.logger)
        if error:
            return error
            
        try:
            # Subclasses should implement this method
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            return create_error_response(str(e))
    
    async def __aenter__(self) -> "BaseAgent":
        """Async context manager entry."""
        await self.setup_events()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_listening()