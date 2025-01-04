"""Core API resources and initialization."""
from ..utils.event_system import EventSystem
from typing import Annotated, Optional
from fastapi import Depends

# Global event system instance
_event_system: Optional[EventSystem] = None

def get_event_system() -> EventSystem:
    """Get the event system instance."""
    global _event_system
    if not _event_system:
        _event_system = EventSystem()
    return _event_system

EventSystemDep = Annotated[EventSystem, Depends(get_event_system)] 