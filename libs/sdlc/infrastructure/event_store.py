from abc import ABC, abstractmethod
import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Set, Union
from uuid import UUID, uuid4
import threading
import time

from ..domain.events import Event, EventMetadata

logger = logging.getLogger(__name__)


class EventStore(ABC):
    """Enhanced abstract base class for event stores"""
    
    @abstractmethod
    def append(self, event: Event) -> None:
        """Append an event to the store"""
        pass
    
    @abstractmethod
    def append_batch(self, events: List[Event]) -> None:
        """Append multiple events in a single batch"""
        pass
    
    @abstractmethod
    def get_events_for_aggregate(self, aggregate_id: UUID, after_version: int = None, target_version: int = None) -> List[Event]:
        """Get all events for a specific aggregate, optionally after a specific version and with version migration"""
        pass
    
    @abstractmethod
    def get_all_events(self) -> List[Event]:
        """Get all events in store"""
        pass
    
    @abstractmethod
    def get_events_by_correlation_id(self, correlation_id: UUID) -> List[Event]:
        """Get all events with a specific correlation ID"""
        pass


class InMemoryEventStore(EventStore):
    """Simple in-memory event store for testing"""
    
    def __init__(self):
        self.events: List[Event] = []
        self.events_by_aggregate: Dict[UUID, List[Event]] = {}
        self.events_by_correlation: Dict[UUID, List[Event]] = {}
    
    def append(self, event: Event) -> None:
        """Append an event to the store"""
        self.events.append(event)
        
        # Index by aggregate
        agg_id = event.aggregate_id
        if agg_id not in self.events_by_aggregate:
            self.events_by_aggregate[agg_id] = []
        self.events_by_aggregate[agg_id].append(event)
        
        # Index by correlation ID
        corr_id = event.metadata.correlation_id
        if corr_id not in self.events_by_correlation:
            self.events_by_correlation[corr_id] = []
        self.events_by_correlation[corr_id].append(event)
    
    def append_batch(self, events: List[Event]) -> None:
        """Append multiple events in a single batch"""
        for event in events:
            self.append(event)
    
    def get_events_for_aggregate(self, aggregate_id: UUID, after_version: int = None, target_version: int = None) -> List[Event]:
        """Get all events for a specific aggregate"""
        events = self.events_by_aggregate.get(aggregate_id, [])
        if after_version is not None:
            events = events[after_version:]
        return events
    
    def get_all_events(self) -> List[Event]:
        """Get all events in store"""
        return self.events
    
    def get_events_by_correlation_id(self, correlation_id: UUID) -> List[Event]:
        """Get all events with a specific correlation ID"""
        return self.events_by_correlation.get(correlation_id, []) 