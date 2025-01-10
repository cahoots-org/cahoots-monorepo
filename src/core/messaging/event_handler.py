"""Event handler for managing event subscriptions and message processing."""
from typing import Dict, Any, Callable, Coroutine, Optional
from src.utils.event_system import EventSystem
from src.utils.base_logger import BaseLogger

class EventHandler:
    """Handles event subscriptions and message processing for agents."""
    
    def __init__(self, 
                 agent_name: str, 
                 event_system: EventSystem,
                 logger: Optional[BaseLogger] = None):
        """Initialize event handler.
        
        Args:
            agent_name: Name of the agent this handler belongs to
            event_system: Event system instance
            logger: Optional logger instance
        """
        self.agent_name = agent_name
        self.logger = logger or BaseLogger(f"{agent_name}EventHandler")
        self.event_system = event_system
        self._handlers: Dict[str, Callable] = {}
        self._listening = False
        
    async def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type.
        
        Args:
            event_type: Type of event to handle
            handler: Coroutine function to handle the event
        """
        self._handlers[event_type] = handler
        if self._listening:
            await self.event_system.subscribe(event_type, self._dispatch_event)
    
    async def unregister_handler(self, event_type: str) -> None:
        """Unregister a handler for an event type.
        
        Args:
            event_type: Type of event to unregister handler for
        """
        if event_type in self._handlers:
            if self._listening:
                await self.event_system.unsubscribe(event_type, self._dispatch_event)
            del self._handlers[event_type]
        
    async def _dispatch_event(self, event_data: Dict[str, Any]) -> None:
        """Dispatch an event to its registered handler.
        
        Args:
            event_data: Event data to process
        """
        event_type = event_data.get("type")
        if event_type in self._handlers:
            try:
                await self._handlers[event_type](event_data)
            except Exception as e:
                self.logger.error(f"Error handling event {event_type}: {str(e)}")
                
    async def start(self) -> None:
        """Start listening for events."""
        if not self._listening:
            self._listening = True
            for event_type in self._handlers:
                await self.event_system.subscribe(event_type, self._dispatch_event)
                
    async def stop(self) -> None:
        """Stop listening for events."""
        if self._listening:
            self._listening = False
            for event_type in self._handlers:
                await self.event_system.unsubscribe(event_type, self._dispatch_event) 