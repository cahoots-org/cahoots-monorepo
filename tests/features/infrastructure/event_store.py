"""In-memory event store implementation for tests"""
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

T = TypeVar('T')


class InMemoryEventStore:
    """Simple in-memory event store for tests"""
    
    def __init__(self):
        """Initialize the event store"""
        self._events: Dict[str, List[Any]] = {}
        self._snapshots: Dict[str, Any] = {}
        self._snapshot_frequency = 100  # Number of events before taking a snapshot
        self._view_store = None
    
    def set_view_store(self, view_store):
        """Set the view store to apply events to"""
        self._view_store = view_store
    
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
        
        # Take a snapshot if any event has a version >= snapshot frequency
        for event in events:
            if hasattr(event, 'version') and event.version >= self._snapshot_frequency:
                self._snapshots[key] = event
            
            # Apply the event to views if a view store is set
            if self._view_store:
                self._view_store.apply_event(event)
    
    def append(self, event: Any) -> None:
        """Append a single event to a stream"""
        stream_id = event.aggregate_id if hasattr(event, 'aggregate_id') else event.entity_id
        self.append_events(stream_id, [event])
    
    def append_batch(self, events: List[Any]) -> None:
        """Append multiple events, possibly to different streams"""
        # Group events by stream
        streams = {}
        for event in events:
            stream_id = event.aggregate_id if hasattr(event, 'aggregate_id') else event.entity_id
            if stream_id not in streams:
                streams[stream_id] = []
            streams[stream_id].append(event)
        
        # Append each group
        for stream_id, stream_events in streams.items():
            self.append_events(stream_id, stream_events)
    
    def get_events(self, stream_id: Any) -> List[Any]:
        """Get all events for a stream"""
        key = str(stream_id)
        return self._events.get(key, [])
    
    def get_all_events(self) -> List[Any]:
        """Get all events in the store"""
        all_events = []
        for events in self._events.values():
            all_events.extend(events)
        return all_events
    
    def get_events_by_type(self, event_type: Type[T]) -> List[T]:
        """Get all events of a specific type"""
        result = []
        for events in self._events.values():
            for event in events:
                if isinstance(event, event_type):
                    result.append(event)
        return result
    
    def get_events_for_aggregate(self, aggregate_id: Any, target_version: Optional[int] = None, after_version: Optional[int] = None) -> List[Any]:
        """Get events for an aggregate"""
        key = str(aggregate_id)
        events = self._events.get(key, [])
        
        if target_version is not None:
            events = [e for e in events if e.version <= target_version]
            
        if after_version is not None:
            events = [e for e in events if e.version > after_version]
            
        return events
    
    def get_events_by_correlation_id(self, correlation_id: Any) -> List[Any]:
        """Get events by correlation ID"""
        result = []
        for events in self._events.values():
            for event in events:
                if hasattr(event, 'metadata') and hasattr(event.metadata, 'correlation_id') and event.metadata.correlation_id == correlation_id:
                    result.append(event)
        return result
    
    def get_latest_snapshot(self, aggregate_id: Any) -> Optional[Any]:
        """Get the latest snapshot for a specific aggregate"""
        return self._snapshots.get(str(aggregate_id))


class InMemoryViewStore:
    """Simple in-memory view store for tests"""
    
    def __init__(self):
        """Initialize the view store"""
        self._views: Dict[str, Dict[str, Any]] = {}
        # Track applied events to ensure idempotency
        self._applied_events: Dict[str, List[str]] = {}
    
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
        
        # Clean up applied events tracking for this view
        if key in self._applied_events:
            del self._applied_events[key]
    
    def apply_event(self, event: Any) -> None:
        """Apply an event to update views"""
        # Get the event ID for tracking
        event_id = str(getattr(event, 'event_id', id(event)))
        
        # Get the aggregate ID from the event
        aggregate_id = event.aggregate_id if hasattr(event, 'aggregate_id') else getattr(event, 'entity_id', None)
        
        if aggregate_id is None:
            # Try common event attribute patterns
            for attr in ['organization_id', 'project_id', 'user_id', 'id']:
                if hasattr(event, attr):
                    aggregate_id = getattr(event, attr)
                    break
        
        if aggregate_id is None:
            print(f"Warning: Could not determine aggregate ID for event {event.__class__.__name__}")
            return
        
        # Keep track of updated views for debugging
        updated_views = []
        aggregate_id_str = str(aggregate_id)
        
        # Apply to all views for this entity
        for key, view in list(self._views.items()):
            # Check if this view has the apply_event method
            if not hasattr(view, 'apply_event'):
                continue
                
            # Check if event is applicable to this view (based on entity ID or global view)
            is_entity_specific_view = aggregate_id_str in key
            should_apply = is_entity_specific_view or view.__class__.__name__.startswith('Global')
            
            if should_apply:
                # Check if we've already applied this event to this view
                if key not in self._applied_events:
                    self._applied_events[key] = []
                    
                if event_id not in self._applied_events[key]:
                    # Apply the event and mark as applied
                    view.apply_event(event)
                    self._applied_events[key].append(event_id)
                    updated_views.append(key)
        
        if not updated_views:
            print(f"Warning: Event {event.__class__.__name__} did not update any views")
        else:
            print(f"Event {event.__class__.__name__} updated views: {', '.join(updated_views)}")