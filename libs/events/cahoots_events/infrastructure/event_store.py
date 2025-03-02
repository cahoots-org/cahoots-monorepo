"""Event store implementation"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID

from ..base import Event, EventMetadata


class EventVersionMigration:
    """Handles event schema versioning and migration"""

    @staticmethod
    def migrate_event(event: Event, target_version: int) -> Event:
        """Migrate an event to a target schema version"""
        if event.version == target_version:
            return event
        # Add migration logic here when needed
        return event


class AggregateSnapshot:
    """Snapshot of aggregate state"""

    def __init__(
        self, aggregate_id: str, aggregate_type: str, state: dict, version: int, timestamp: datetime
    ):
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.state = state
        self.version = version
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert snapshot to dictionary"""
        return {
            "aggregate_id": str(self.aggregate_id),
            "aggregate_type": self.aggregate_type,
            "state": self.state,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AggregateSnapshot":
        """Create snapshot from dictionary"""
        return cls(
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            state=data["state"],
            version=data["version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class EventBatch:
    """Batch of events for atomic storage"""

    def __init__(self, events: List[Event], batch_id: UUID = None):
        self.events = events
        self.batch_id = batch_id or UUID()

    def to_dict(self) -> dict:
        """Convert batch to dictionary"""
        return {
            "batch_id": str(self.batch_id),
            "events": [EventSerializer.serialize_event(e) for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventBatch":
        """Create batch from dictionary"""
        return cls(
            events=[EventSerializer.deserialize_event(e) for e in data["events"]],
            batch_id=UUID(data["batch_id"]),
        )


class EventSerializer:
    """Serializes and deserializes events"""

    @staticmethod
    def serialize_event(event: Event) -> dict:
        """Convert event to dictionary"""
        metadata = {
            "schema_version": event.metadata.schema_version,
            "causation_id": (
                str(event.metadata.causation_id) if event.metadata.causation_id else None
            ),
            "correlation_id": (
                str(event.metadata.correlation_id) if event.metadata.correlation_id else None
            ),
            "created_at": event.metadata.created_at.isoformat(),
            "actor_id": str(event.metadata.actor_id) if event.metadata.actor_id else None,
            "context": event.metadata.context,
        }

        return {
            "event_type": event.__class__.__name__,
            "event_id": str(event.event_id),
            "timestamp": event.timestamp.isoformat(),
            "metadata": metadata,
            "data": {
                k: str(v) if isinstance(v, UUID) else v
                for k, v in event.__dict__.items()
                if k not in {"event_id", "timestamp", "metadata"}
            },
        }

    @staticmethod
    def deserialize_event(event_data: dict, target_version: int = None) -> Event:
        """Create event from dictionary"""
        # Import all event classes
        from .. import auth, code_changes, organization, project, team

        event_classes = {
            cls.__name__: cls
            for module in [auth, organization, team, project, code_changes]
            for cls in module.__dict__.values()
            if isinstance(cls, type) and issubclass(cls, Event) and cls != Event
        }

        event_type = event_data["event_type"]
        if event_type not in event_classes:
            raise ValueError(f"Unknown event type: {event_type}")

        event_class = event_classes[event_type]
        metadata = EventMetadata(
            schema_version=event_data["metadata"]["schema_version"],
            causation_id=(
                UUID(event_data["metadata"]["causation_id"])
                if event_data["metadata"]["causation_id"]
                else None
            ),
            correlation_id=(
                UUID(event_data["metadata"]["correlation_id"])
                if event_data["metadata"]["correlation_id"]
                else None
            ),
            created_at=datetime.fromisoformat(event_data["metadata"]["created_at"]),
            actor_id=(
                UUID(event_data["metadata"]["actor_id"])
                if event_data["metadata"]["actor_id"]
                else None
            ),
            context=event_data["metadata"]["context"],
        )

        # Convert UUIDs in data
        data = {}
        for k, v in event_data["data"].items():
            if k.endswith("_id") and isinstance(v, str):
                try:
                    data[k] = UUID(v)
                except ValueError:
                    data[k] = v
            else:
                data[k] = v

        event = event_class(
            event_id=UUID(event_data["event_id"]),
            timestamp=datetime.fromisoformat(event_data["timestamp"]),
            metadata=metadata,
            **data,
        )

        if target_version is not None and event.version != target_version:
            event = EventVersionMigration.migrate_event(event, target_version)

        return event


class EventStore(ABC):
    """Abstract base class for event stores"""

    @abstractmethod
    def append(self, event: Event) -> None:
        """Append a single event"""
        pass

    @abstractmethod
    def append_batch(self, events: List[Event]) -> None:
        """Append multiple events atomically"""
        pass

    @abstractmethod
    def get_events_for_aggregate(
        self, aggregate_id: UUID, after_version: int = None, target_version: int = None
    ) -> List[Event]:
        """Get all events for an aggregate"""
        pass

    @abstractmethod
    def get_all_events(self) -> List[Event]:
        """Get all events"""
        pass

    @abstractmethod
    def get_events_by_correlation_id(self, correlation_id: UUID) -> List[Event]:
        """Get events by correlation ID"""
        pass

    @abstractmethod
    def save_snapshot(self, snapshot: AggregateSnapshot) -> None:
        """Save aggregate snapshot"""
        pass

    @abstractmethod
    def get_latest_snapshot(self, aggregate_id: Union[str, UUID]) -> Optional[AggregateSnapshot]:
        """Get latest snapshot for aggregate"""
        pass


class InMemoryEventStore(EventStore):
    """In-memory implementation of event store"""

    def __init__(self):
        self.events: List[Event] = []
        self.snapshots: Dict[str, AggregateSnapshot] = {}

    def append(self, event: Event) -> None:
        """Append a single event"""
        self.events.append(event)

    def append_batch(self, events: List[Event]) -> None:
        """Append multiple events atomically"""
        self.events.extend(events)

    def get_events_for_aggregate(
        self, aggregate_id: UUID, after_version: int = None, target_version: int = None
    ) -> List[Event]:
        """Get all events for an aggregate"""
        events = [e for e in self.events if e.aggregate_id == aggregate_id]
        if after_version is not None:
            events = events[after_version:]
        if target_version is not None:
            events = [EventVersionMigration.migrate_event(e, target_version) for e in events]
        return events

    def get_all_events(self) -> List[Event]:
        """Get all events"""
        return self.events.copy()

    def get_events_by_correlation_id(self, correlation_id: UUID) -> List[Event]:
        """Get events by correlation ID"""
        return [e for e in self.events if e.metadata.correlation_id == correlation_id]

    def save_snapshot(self, snapshot: AggregateSnapshot) -> None:
        """Save aggregate snapshot"""
        self.snapshots[str(snapshot.aggregate_id)] = snapshot

    def get_latest_snapshot(self, aggregate_id: Union[str, UUID]) -> Optional[AggregateSnapshot]:
        """Get latest snapshot for aggregate"""
        return self.snapshots.get(str(aggregate_id))
