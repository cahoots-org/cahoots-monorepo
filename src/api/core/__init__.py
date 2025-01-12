"""Core API functionality."""

from typing import Optional
from src.event_system import EventSystem

_event_system: Optional[EventSystem] = None

def get_event_system() -> EventSystem:
    """Get the global event system instance."""
    if _event_system is None:
        raise RuntimeError("Event system not initialized")
    return _event_system

def set_event_system(event_system: EventSystem) -> None:
    """Set the global event system instance."""
    global _event_system
    _event_system = event_system 