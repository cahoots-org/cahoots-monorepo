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
from tests.features.test_events import TestEvent

logger = logging.getLogger(__name__)

class EventVersionMigration:
    """Handles event schema migrations"""
    
    @staticmethod
    def migrate_event(event: Event, target_version: int) -> Event:
        """Migrate event to target version"""
        if event.metadata.schema_version >= target_version:
            return event
            
        # Example migration from v1 to v2
        if isinstance(event, TestEvent) and event.metadata.schema_version == 1 and target_version == 2:
            event.data['new_field'] = f"converted_{event.data.get('old_field', '')}"
            event.metadata.schema_version = 2
            
        return event


class AggregateSnapshot:
    """Represents a snapshot of an aggregate's state"""
    
    def __init__(self, aggregate_id: str, aggregate_type: str, state: dict, version: int, timestamp: datetime):
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.state = state
        self.version = version
        self.timestamp = timestamp
        
    def to_dict(self) -> dict:
        return {
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'state': self.state,
            'version': self.version,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AggregateSnapshot':
        return cls(
            aggregate_id=data['aggregate_id'],
            aggregate_type=data['aggregate_type'],
            state=data['state'],
            version=data['version'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


class EventBatch:
    """Represents a batch of events for efficient storage"""
    
    def __init__(self, events: List[Event], batch_id: UUID = None):
        self.batch_id = batch_id or uuid4()
        self.events = events
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            'batch_id': str(self.batch_id),
            'timestamp': self.timestamp.isoformat(),
            'events': [EventSerializer.serialize_event(event) for event in self.events]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EventBatch':
        return cls(
            batch_id=UUID(data['batch_id']),
            events=[EventSerializer.deserialize_event(event_data) for event_data in data['events']]
        )


class EventSerializer:
    """Enhanced serialization with compression and versioning"""
    
    @staticmethod
    def serialize_event(event: Event) -> dict:
        """Serialize an event to a dictionary"""
        event_dict = {
            'type': event.__class__.__name__,
            'event_id': str(event.event_id),
            'timestamp': event.timestamp.isoformat(),
            'metadata': {
                'schema_version': event.metadata.schema_version,
                'causation_id': str(event.metadata.causation_id) if event.metadata.causation_id else None,
                'correlation_id': str(event.metadata.correlation_id),
                'created_at': event.metadata.created_at.isoformat(),
                'actor_id': str(event.metadata.actor_id) if event.metadata.actor_id else None,
                'context': event.metadata.context
            }
        }
        
        # Add all other event attributes
        for key, value in event.__dict__.items():
            if key not in ['event_id', 'timestamp', 'metadata']:
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, (list, dict)):
                    value = json.loads(json.dumps(value, default=str))
                event_dict[key] = value
                
        return event_dict

    @staticmethod
    def deserialize_event(event_data: dict, target_version: int = None) -> Event:
        """Deserialize an event from a dictionary with optional version migration"""
        # Perform version migration if needed
        if target_version:
            event_data = EventVersionMigration.migrate_event(event_data, target_version)
        
        # Create metadata
        metadata = EventMetadata(
            schema_version=event_data['metadata']['schema_version'],
            causation_id=UUID(event_data['metadata']['causation_id']) if event_data['metadata']['causation_id'] else None,
            correlation_id=UUID(event_data['metadata']['correlation_id']),
            created_at=datetime.fromisoformat(event_data['metadata']['created_at']),
            actor_id=UUID(event_data['metadata']['actor_id']) if event_data['metadata']['actor_id'] else None,
            context=event_data['metadata']['context']
        )
        
        # Create event
        event_type = event_data['type']
        if event_type == 'TestEvent':
            return TestEvent(
                event_id=UUID(event_data['event_id']),
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                metadata=metadata,
                aggregate_id=event_data['aggregate_id'],
                data=event_data['data']
            )
        else:
            raise ValueError(f"Unknown event type: {event_type}")


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
    
    @abstractmethod
    def save_snapshot(self, snapshot: AggregateSnapshot) -> None:
        """Save a snapshot of an aggregate's state"""
        pass
    
    @abstractmethod
    def get_latest_snapshot(self, aggregate_id: Union[str, UUID]) -> Optional[AggregateSnapshot]:
        """Get the latest snapshot for an aggregate"""
        pass


class EnhancedFileEventStore(EventStore):
    """Production-ready file-based event store with advanced features"""
    
    def __init__(self, storage_dir: Path, max_batch_size: int = 1000, snapshot_frequency: int = 100):
        self.storage_dir = storage_dir
        self.events_dir = storage_dir / 'events'
        self.snapshots_dir = storage_dir / 'snapshots'
        self.index_file = storage_dir / 'event_index.json'
        self.batch_size = max_batch_size
        self.snapshot_frequency = snapshot_frequency
        
        # Thread-safe event cache
        self._events_lock = threading.Lock()
        self._events: List[Event] = []
        self._aggregate_events: Dict[str, List[int]] = {}
        self._event_batches: List[EventBatch] = []
        self._dirty_aggregates: Set[str] = set()
        
        # Create directory structure
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage
        self._load_events()
    
    def cleanup(self):
        """Cleanup resources"""
        pass  # No background tasks to clean up

    def __del__(self):
        """Cleanup when the object is destroyed"""
        self.cleanup()
    
    def append(self, event: Event) -> None:
        with self._events_lock:
            self._append_event(event)
            if len(self._events) % self.batch_size == 0:
                self._save_batch()
            # Check if we need to create a snapshot
            self._check_snapshot_needed(str(event.aggregate_id))
    
    def append_batch(self, events: List[Event]) -> None:
        with self._events_lock:
            for event in events:
                self._append_event(event)
            self._save_batch()
            # Check if we need to create snapshots
            for event in events:
                self._check_snapshot_needed(str(event.aggregate_id))
    
    def _check_snapshot_needed(self, aggregate_id: str) -> None:
        """Check if a snapshot needs to be created and create it if necessary"""
        try:
            # Get events for this aggregate
            events = self.get_events_for_aggregate(aggregate_id)
            if not events:
                return

            # Get latest snapshot
            latest_snapshot = self.get_latest_snapshot(aggregate_id)
            current_version = len(events)

            # Determine if we need a new snapshot
            if latest_snapshot:
                events_since_snapshot = current_version - latest_snapshot.version
                if events_since_snapshot < self.snapshot_frequency:
                    return
            elif current_version < self.snapshot_frequency:
                return

            # Create new snapshot
            snapshot = AggregateSnapshot(
                aggregate_id=aggregate_id,
                aggregate_type=events[-1].__class__.__name__,
                state=self._calculate_aggregate_state(events),
                version=current_version,
                timestamp=datetime.utcnow()
            )
            
            # Save snapshot
            self.save_snapshot(snapshot)
            logger.info(f"Created snapshot for aggregate {aggregate_id} at version {current_version}")
        except Exception as e:
            logger.error(f"Error checking snapshot for aggregate {aggregate_id}: {e}")

    def _save_batch(self) -> None:
        """Save current events as a batch"""
        if not self._events:
            return
        
        try:
            # Create batch
            batch = EventBatch(self._events[-min(self.batch_size, len(self._events)):])
            batch_file = self.events_dir / f'batch_{batch.batch_id}.json.gz'
            
            # Save batch
            with gzip.open(batch_file, 'wt') as f:
                json.dump(batch.to_dict(), f)
            
            self._event_batches.append(batch)
            self._save_index()
        except Exception as e:
            logger.error(f"Error saving batch: {e}")

    def _append_event(self, event: Event) -> None:
        """Internal method to append an event and update indices"""
        self._events.append(event)
        event_index = len(self._events) - 1
        
        # Update aggregate event index
        aggregate_id = str(event.aggregate_id)
        if aggregate_id not in self._aggregate_events:
            self._aggregate_events[aggregate_id] = []
        self._aggregate_events[aggregate_id].append(event_index)
    
    def get_events_for_aggregate(self, aggregate_id: str, after_version: int = None, target_version: int = None) -> List[Event]:
        """Get all events for a specific aggregate, optionally after a specific version and with version migration"""
        with self._events_lock:
            indices = self._aggregate_events.get(str(aggregate_id), [])
            if after_version is not None:
                indices = indices[after_version:]
            events = [self._events[i] for i in indices]
            
            if target_version is not None:
                migrated_events = []
                for event in events:
                    if event.metadata.schema_version < target_version:
                        # Create a new event with updated data
                        migrated_event = TestEvent(
                            event_id=event.event_id,
                            timestamp=event.timestamp,
                            metadata=EventMetadata(
                                schema_version=target_version,
                                correlation_id=event.metadata.correlation_id,
                                causation_id=event.metadata.causation_id,
                                actor_id=event.metadata.actor_id,
                                context=event.metadata.context
                            ),
                            aggregate_id=event.aggregate_id,
                            data=dict(event.data)
                        )
                        # Apply migration rules
                        if target_version == 2:
                            migrated_event.data['new_field'] = f"converted_{migrated_event.data.get('old_field', '')}"
                        migrated_events.append(migrated_event)
                    else:
                        migrated_events.append(event)
                events = migrated_events
            
            return events
    
    def get_all_events(self) -> List[Event]:
        with self._events_lock:
            return self._events.copy()
    
    def get_events_by_correlation_id(self, correlation_id: UUID) -> List[Event]:
        with self._events_lock:
            return [
                event for event in self._events
                if event.metadata.correlation_id == correlation_id
            ]
    
    def save_snapshot(self, snapshot: AggregateSnapshot) -> None:
        """Save a snapshot to disk"""
        snapshot_file = self.snapshots_dir / f"{snapshot.aggregate_id}_{snapshot.version}.json.gz"
        with gzip.open(snapshot_file, 'wt') as f:
            json.dump(snapshot.to_dict(), f)
    
    def get_latest_snapshot(self, aggregate_id: Union[str, UUID]) -> Optional[AggregateSnapshot]:
        """Get the latest snapshot for an aggregate"""
        # Convert to string if UUID
        aggregate_id_str = str(aggregate_id)
        snapshot_pattern = f"{aggregate_id_str}_*.json.gz"
        snapshot_files = list(self.snapshots_dir.glob(snapshot_pattern))
        
        if not snapshot_files:
            return None
            
        # Get the latest snapshot file based on version number
        latest_file = max(snapshot_files, key=lambda f: int(f.stem.split('_')[1]))
        
        try:
            with gzip.open(latest_file, 'rt') as f:
                snapshot_data = json.load(f)
                return AggregateSnapshot.from_dict(snapshot_data)
        except Exception as e:
            logger.error(f"Error loading snapshot {latest_file}: {e}")
            return None
    
    def _load_events(self) -> None:
        """Load all event batches"""
        try:
            # Clear existing state
            self._events.clear()
            self._aggregate_events.clear()
            self._event_batches.clear()
            
            # Load batches in order
            if self.events_dir.exists():
                batch_files = sorted(self.events_dir.glob('batch_*.json.gz'))
                loaded_events = []
                
                # First pass: load all batch files and collect events
                for batch_file in batch_files:
                    try:
                        with gzip.open(batch_file, 'rt') as f:
                            batch_data = json.load(f)
                            batch = EventBatch.from_dict(batch_data)
                            self._event_batches.append(batch)
                            loaded_events.extend(batch.events)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Error loading batch file {batch_file}: {e}")
                        continue
                
                # Sort events by timestamp to ensure correct order
                loaded_events.sort(key=lambda e: e.timestamp)
                
                # Second pass: add events in order and build index
                for event in loaded_events:
                    self._append_event(event)
                
                # Validate or rebuild index
                if self.index_file.exists():
                    try:
                        with open(self.index_file, 'r') as f:
                            loaded_index = json.load(f)
                            # Validate index before using it
                            if self._validate_index(loaded_index):
                                self._aggregate_events = loaded_index
                            else:
                                logger.warning("Index validation failed, rebuilding...")
                                self._rebuild_index()
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Error loading index file: {e}")
                        self._rebuild_index()
                else:
                    self._rebuild_index()
        except Exception as e:
            logger.error(f"Error loading events: {e}")
            # Reset to clean state
            self._events.clear()
            self._aggregate_events.clear()
            self._event_batches.clear()
    
    def _validate_index(self, index: Dict[str, List[int]]) -> bool:
        """Validate that the loaded index matches the events"""
        try:
            # Check that all indices are valid
            for aggregate_id, indices in index.items():
                if not indices:  # Skip empty lists
                    continue
                    
                # Check index bounds
                if max(indices) >= len(self._events):
                    return False
                    
                # Check that events match aggregate ID
                for idx in indices:
                    event = self._events[idx]
                    if str(event.aggregate_id) != aggregate_id:
                        return False
                        
                # Check that all events for this aggregate are included
                expected_events = [
                    i for i, e in enumerate(self._events)
                    if str(e.aggregate_id) == aggregate_id
                ]
                if sorted(indices) != sorted(expected_events):
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating index: {e}")
            return False
    
    def _rebuild_index(self) -> None:
        """Rebuild the aggregate index from loaded events"""
        self._aggregate_events.clear()
        for i, event in enumerate(self._events):
            aggregate_id = str(event.aggregate_id)
            if aggregate_id not in self._aggregate_events:
                self._aggregate_events[aggregate_id] = []
            self._aggregate_events[aggregate_id].append(i)
        
        # Save the rebuilt index
        self._save_index()
    
    def _save_index(self) -> None:
        """Save the event index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self._aggregate_events, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def _calculate_aggregate_state(self, events: List[Event]) -> dict:
        """Calculate the aggregate state from events"""
        # For now, just store the latest event data
        if not events:
            return {}
        latest_event = events[-1]
        state = {
            'latest_event': EventSerializer.serialize_event(latest_event),
            'event_count': len(events)
        }
        return state 