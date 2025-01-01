"""Core API resources and initialization."""
from ..utils.event_system import EventSystem
from typing import Annotated, Optional
from fastapi import Depends

# Initialize shared resources
_event_system: Optional[EventSystem] = None

def get_event_system() -> EventSystem:
    """Get the event system instance.
    
    Returns:
        EventSystem: The shared event system instance
    """
    global _event_system
    if _event_system is None:
        _event_system = EventSystem()
    return _event_system

# Export event system instance
event_system = _event_system 