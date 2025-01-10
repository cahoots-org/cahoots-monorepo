# src/agents/base_agent.py
from typing import Dict, Any, Optional
import logging
import asyncio
import json
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from src.utils.event_system import EventSystem
from src.utils.model import Model
from src.utils.base_logger import BaseLogger
from src.utils.task_manager import TaskManager
from src.core.messaging import (
    validate_story_assignment,
    validate_message_type,
    create_success_response,
    create_error_response
)
from src.core.messaging.event_handler import EventHandler

class BaseAgent(ABC):
    """Base agent class with shared functionality."""
    
    def __init__(self, model_name: str, event_system: EventSystem, start_listening: bool = True):
        """Initialize base agent.
        
        Args:
            model_name: Name of the model to use
            event_system: Event system instance
            start_listening: Whether to start listening for events immediately
            
        Raises:
            Exception: If initialization fails
        """
        self.logger = BaseLogger(self.__class__.__name__)
        
        try:
            self.logger.debug(f"Initializing {self.__class__.__name__} with model {model_name}")
            
            # Set up event handler
            self.event_system = event_system
            self.event_handler = EventHandler(
                agent_name=self.__class__.__name__,
                event_system=self.event_system,
                logger=self.logger
            )
            
            # Set up model
            self.model_name = model_name
            self.model = Model(model_name)
            
            # Set up task manager
            self._task_manager = TaskManager(self.__class__.__name__)
            self.task_manager = self._task_manager  # Public access for testing
            
            # Start health check task
            self._task_manager.create_task(self._update_health_status())
            
            if start_listening:
                self._task_manager.create_task(self.start())
                
            self.logger.info(f"{self.__class__.__name__} base initialization complete")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
            
    async def _update_health_status(self):
        """Periodically update health status in Redis."""
        while True:
            try:
                health_key = f"health:{self.__class__.__name__}"
                health_data = {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "agent_type": self.__class__.__name__
                }
                await self.event_system.redis.set(health_key, json.dumps(health_data))
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                self.logger.error(f"Failed to update health status: {str(e)}")
                await asyncio.sleep(1)  # Shorter sleep on error
            
    async def setup_events(self) -> None:
        """Initialize event system and register handlers.
        
        This should be overridden by subclasses to set up their specific event handlers.
        """
        # Connect if not already connected
        if not self.event_system.is_connected:
            await self.event_system.connect()
            
        # Register default handlers
        await self.event_handler.register_handler("system", self.handle_system_message)
        await self.event_handler.register_handler("story_assigned", self.handle_story_assigned)
            
    async def start(self) -> None:
        """Start the agent's event handling and processing."""
        await self.setup_events()
        await self.event_handler.start()
            
    async def stop(self) -> None:
        """Stop the agent's event handling and processing."""
        await self.event_handler.stop()
        await self._task_manager.cancel_all()
        # Clean up health status
        health_key = f"health:{self.__class__.__name__}"
        self.event_system.redis.delete(health_key)  # Redis delete is synchronous
            
    @abstractmethod
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: System message data
        """
        pass
            
    @abstractmethod
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment messages.
        
        Args:
            message: Story assignment data
            
        Returns:
            Dict[str, Any]: Response indicating success or failure
        """
        pass
            
    @asynccontextmanager
    async def managed_operation(self):
        """Context manager for handling agent operations with proper cleanup.
        
        Usage:
            async with agent.managed_operation():
                await agent.do_work()
        """
        try:
            await self.start()
            yield self
        finally:
            await self.stop()