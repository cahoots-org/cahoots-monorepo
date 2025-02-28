"""In-memory event store implementation for tests"""
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

T = TypeVar('T')


class InMemoryEventStore:
    """Simple in-memory event store for tests"""
    
    def __init__(self):
        """Initialize the event store"""
        self._events: Dict[str, List[Any]] = {}
    
    def append_events(self, stream_id: Any, events: List[Any], expected_version: Optional[int] = None) -> None:
        """Append events to a stream"""
        key = str(stream_id)
        if key not in self._events:
            self._events[key] = []
        
        if expected_version is not None:
            current_version = len(self._events[key])
            if current_version != expected_version:
                raise ValueError(f"Concurrency error: expected version {expected_version}, got {current_version}")
        
        self._events[key].extend(events)
    
    def get_events(self, stream_id: Any) -> List[Any]:
        """Get all events for a stream"""
        key = str(stream_id)
        return self._events.get(key, [])
    
    def get_events_by_type(self, event_type: Type[T]) -> List[T]:
        """Get all events of a specific type"""
        result = []
        for events in self._events.values():
            for event in events:
                if isinstance(event, event_type):
                    result.append(event)
        return result 


class InMemoryViewStore:
    """Simple in-memory view store for tests"""
    
    def __init__(self):
        """Initialize the view store"""
        self._views: Dict[str, Dict[str, Any]] = {}
    
    def get_view(self, entity_id: Any, view_class: Type[T]) -> Optional[T]:
        """Get a view for an entity"""
        key = f"{view_class.__name__}:{entity_id}"
        if key in self._views:
            return self._views[key]
        
        # Create a new view
        view = view_class(entity_id)
        self._views[key] = view
        return view
    
    def save_view(self, entity_id: Any, view: Any) -> None:
        """Save a view for an entity"""
        key = f"{view.__class__.__name__}:{entity_id}"
        self._views[key] = view
    
    def delete_view(self, entity_id: Any, view_class: Type) -> None:
        """Delete a view for an entity"""
        key = f"{view_class.__name__}:{entity_id}"
        if key in self._views:
            del self._views[key] 