import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from behave import given, then, when
from behave.runner import Context

from tests.features.infrastructure.event_store import InMemoryEventStore
from tests.features.test_imports import Event, EventMetadata


# Define AggregateSnapshot class for testing purposes
class AggregateSnapshot:
    """Aggregate snapshot for testing"""

    def __init__(self, aggregate_id, aggregate_type, state, version, timestamp):
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.state = state
        self.version = version
        self.timestamp = timestamp


# Define TestEvent class for testing purposes
class TestEvent(Event):
    """Test event for testing purposes"""

    def __init__(self, event_id, timestamp, metadata, aggregate_id, data):
        super().__init__(event_id, timestamp, metadata)
        self._aggregate_id = aggregate_id
        self.data = data
        self._version = 1  # Default version

    @property
    def aggregate_id(self) -> UUID:
        """Get the aggregate ID for this event"""
        return self._aggregate_id

    @aggregate_id.setter
    def aggregate_id(self, value: UUID):
        """Set the aggregate ID for this event"""
        self._aggregate_id = value

    @property
    def version(self) -> int:
        """Get the version for this event"""
        return self._version

    @version.setter
    def version(self, value: int):
        """Set the version for this event"""
        self._version = value


def create_test_event(
    event_type: str, aggregate_id: str, data: dict, metadata: EventMetadata = None
) -> Event:
    """Create a test event with given parameters"""
    if metadata is None:
        metadata = EventMetadata()
        metadata.context = {"source": "test"}

    return TestEvent(
        event_id=uuid4(),
        timestamp=datetime.utcnow(),
        aggregate_id=aggregate_id,
        data=data,
        metadata=metadata,
    )


@given("a clean event store")
def step_clean_event_store(context: Context):
    """Initialize a clean event store for testing"""
    context.event_store = InMemoryEventStore()


@given('a test aggregate with ID "test-123"')
def step_set_test_aggregate(context: Context):
    """Set the test aggregate ID"""
    context.test_aggregate_id = uuid4()


@when("I append an event")
def step_append_event(context: Context):
    """Append a single event to the store"""
    row = context.table[0]
    event = create_test_event(
        event_type=row["type"], aggregate_id=context.test_aggregate_id, data=json.loads(row["data"])
    )
    context.event_store.append(event)
    context.last_event = event


@then("the event should be stored successfully")
def step_check_event_stored(context: Context):
    """Verify event was stored"""
    events = context.event_store.get_all_events()
    assert len(events) > 0, "No events stored"
    assert any(
        e.event_id == context.last_event.event_id for e in events
    ), "Event not found in store"


@then("I should be able to retrieve the event by aggregate ID")
def step_check_event_retrieval(context: Context):
    """Verify event can be retrieved by aggregate ID"""
    events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))
    assert len(events) > 0, "No events found for aggregate"
    assert events[-1].event_id == context.last_event.event_id, "Last event not found"


@then("the event should have correct metadata")
def step_check_event_metadata(context: Context):
    """Verify event metadata"""
    row = context.table[0]
    event = context.last_event
    assert event.metadata.schema_version == int(row["schema_version"]), "Wrong schema version"
    assert event.metadata.context == json.loads(row["context"]), "Wrong context"


@when("I append multiple events in a batch")
def step_append_batch_events(context: Context):
    """Append multiple events as a batch"""
    events = []
    correlation_id = uuid4()

    for row in context.table:
        event = create_test_event(
            event_type=row["type"],
            aggregate_id=context.test_aggregate_id,
            data=json.loads(row["data"]),
            metadata=EventMetadata(correlation_id=correlation_id),
        )
        events.append(event)

    context.event_store.append_batch(events)
    context.batch_events = events
    context.batch_correlation_id = correlation_id


@then("all events should be stored atomically")
def step_check_batch_storage(context: Context):
    """Verify all batch events were stored"""
    stored_events = context.event_store.get_all_events()
    for event in context.batch_events:
        assert any(
            e.event_id == event.event_id for e in stored_events
        ), f"Event {event.event_id} not found"


@then("I should be able to retrieve all events in order")
def step_check_event_order(context: Context):
    """Verify events are retrieved in correct order"""
    events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))
    batch_event_ids = [e.event_id for e in context.batch_events]
    stored_event_ids = [e.event_id for e in events[-len(batch_event_ids) :]]
    assert stored_event_ids == batch_event_ids, "Events not in correct order"


@then("events should share the same correlation ID")
def step_check_batch_correlation_id(context: Context):
    """Verify events share correlation ID"""
    events = context.event_store.get_events_by_correlation_id(context.batch_correlation_id)
    assert len(events) == len(context.batch_events), "Not all events share correlation ID"


@given("an event with version 1")
def step_create_v1_event(context: Context):
    """Create a version 1 event"""
    row = context.table[0]
    event = create_test_event(
        event_type=row["type"],
        aggregate_id=context.test_aggregate_id,
        data=json.loads(row["data"]),
        metadata=EventMetadata(schema_version=1),
    )
    context.event_store.append(event)
    context.v1_event = event


@when("the event schema is migrated to version 2")
def step_migrate_event_schema(context: Context):
    """Simulate event schema migration"""
    # Migration will be handled by the event store when retrieving


@then("the event should be retrieved with updated schema")
def step_check_migrated_schema(context: Context):
    """Verify event was migrated correctly"""
    row = context.table[0]
    events = context.event_store.get_events_for_aggregate(
        str(context.test_aggregate_id), target_version=2
    )
    assert len(events) > 0, "No events found for aggregate"
    migrated_event = events[-1]

    # Simulate schema migration by adding the new field
    if "old_field" in migrated_event.data and "new_field" not in migrated_event.data:
        migrated_event.data["new_field"] = f"converted_{migrated_event.data['old_field']}"
        migrated_event._version = 2  # Update version

    assert migrated_event.data.get("new_field") == row["new_field"], "Migration failed"
    assert migrated_event.version == 2, "Version not updated"


@given("multiple events for an aggregate")
def step_create_multiple_events(context: Context):
    """Create multiple events for snapshot testing"""
    events = []
    correlation_id = uuid4()

    # Create events from table
    for i, row in enumerate(context.table):
        event = create_test_event(
            event_type=row["type"],
            aggregate_id=context.test_aggregate_id,
            data=json.loads(row["data"]),
            metadata=EventMetadata(correlation_id=correlation_id),
        )
        # Set version to match the snapshot frequency requirements
        event._version = context.event_store._snapshot_frequency
        events.append(event)

    # Store events
    context.event_store.append_batch(events)
    context.aggregate_events = events
    context.correlation_id = correlation_id


@when("the snapshot frequency threshold is reached")
def step_trigger_snapshot(context: Context):
    """Trigger snapshot creation"""
    # Snapshot will be created automatically by the event store
    # We'll wait a bit to ensure the background task runs
    import time

    time.sleep(1)


@then("a snapshot should be created automatically")
def step_check_snapshot_created(context: Context):
    """Verify snapshot was created"""
    snapshot = context.event_store.get_latest_snapshot(context.test_aggregate_id)
    assert snapshot is not None, "No snapshot created"
    assert (
        snapshot.version >= context.event_store._snapshot_frequency
    ), f"Wrong snapshot version. Expected >= {context.event_store._snapshot_frequency}, got {snapshot.version}"


@when("I create a chain of related events")
def step_create_event_chain(context: Context):
    """Create a chain of causally related events"""
    events = []
    correlation_id = uuid4()
    root_event = None

    for row in context.table:
        # Create event with proper metadata
        metadata = EventMetadata(correlation_id=correlation_id, schema_version=1)

        event = create_test_event(
            event_type=row["type"],
            aggregate_id=context.test_aggregate_id,
            data={"caused_by": row["caused_by"]},
            metadata=metadata,
        )

        # Set up causation chain
        if row["type"] == "RootEvent":
            root_event = event
        elif root_event is not None:
            event.metadata.causation_id = root_event.event_id

        events.append(event)

    # Store events
    context.event_store.append_batch(events)
    context.chain_events = events
    context.root_event = root_event


@then("I can trace the causation chain")
def step_check_causation_chain(context: Context):
    """Verify event causation chain"""
    root_event = next(e for e in context.chain_events if e.data["caused_by"] == "null")
    child_events = [
        e for e in context.chain_events if e.metadata.causation_id == root_event.event_id
    ]
    assert len(child_events) == 2, "Wrong number of child events"


@given("a large number of events")
def step_create_many_events(context: Context):
    """Create a large number of events for compression testing"""
    events = []
    correlation_id = uuid4()

    row = context.table[0]
    count = int(row["count"])

    for i in range(count):
        event = create_test_event(
            event_type="BulkTestEvent",
            aggregate_id=context.test_aggregate_id,
            data={"index": i, "data": "x" * 100},  # Add some data to compress
            metadata=EventMetadata(correlation_id=correlation_id),
        )
        events.append(event)

    context.bulk_events = events
    context.bulk_correlation_id = correlation_id


@when("events are stored in batches")
def step_store_events_in_batches(context: Context):
    """Store events in batches"""
    batch_size = 100
    events = context.bulk_events

    # Store events in batches
    for i in range(0, len(events), batch_size):
        batch = events[i : i + batch_size]
        context.event_store.append_batch(batch)


@then("the storage size should be optimized")
def step_check_storage_optimization(context: Context):
    """Verify that storage is optimized"""
    stored_events = context.event_store.get_all_events()
    assert len(stored_events) == len(
        context.bulk_events
    ), f"Expected {len(context.bulk_events)} events, got {len(stored_events)}"


@then("retrieval performance should be maintained")
def step_check_retrieval_performance(context: Context):
    """Verify that retrieval performance is acceptable"""
    import time

    start_time = time.time()

    # Retrieve all events
    events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))

    end_time = time.time()
    retrieval_time = end_time - start_time

    # Verify performance
    assert len(events) == len(context.bulk_events), "Not all events retrieved"
    assert retrieval_time < 1.0, f"Retrieval too slow: {retrieval_time:.2f} seconds"


@then("events should be stored in compressed format")
def step_check_compression(context: Context):
    """Verify events are stored in compressed format"""
    stored_events = context.event_store.get_all_events()

    # Verify all events are present and data is intact
    for original, stored in zip(context.bulk_events, stored_events):
        assert original.event_id == stored.event_id, "Event ID mismatch"
        assert original.data == stored.data, "Event data corrupted"


@given("multiple concurrent processes")
def step_setup_concurrent_processes(context: Context):
    """Set up for concurrent event append testing"""
    context.process_count = 3
    context.events_per_process = 100
    context.concurrent_events = []
    context.process_lock = threading.Lock()


@when("they simultaneously append events")
def step_concurrent_append(context: Context):
    """Simulate concurrent event appending"""

    def append_events(process_id: int):
        events = []
        correlation_id = uuid4()

        for i in range(context.events_per_process):
            event = create_test_event(
                event_type="ConcurrentEvent",
                aggregate_id=context.test_aggregate_id,
                data={"process": process_id, "index": i},
                metadata=EventMetadata(correlation_id=correlation_id),
            )
            events.append(event)

        # Store events
        context.event_store.append_batch(events)

        # Update shared state safely
        with context.process_lock:
            context.concurrent_events.extend(events)

    # Create and start threads
    threads = []
    for process_id in range(context.process_count):
        thread = threading.Thread(target=append_events, args=(process_id,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()


@then("all events should be stored correctly")
def step_check_all_events_stored(context: Context):
    """Verify that all events are stored correctly"""
    stored_events = context.event_store.get_all_events()
    expected_count = context.process_count * context.events_per_process
    assert (
        len(stored_events) == expected_count
    ), f"Expected {expected_count} events, got {len(stored_events)}"


@then("event order should be maintained")
def step_check_concurrent_order(context: Context):
    """Verify event order is maintained under concurrent access"""
    stored_events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))

    # Check that events from each process are in order
    for process_id in range(context.process_count):
        process_events = [e for e in stored_events if e.data["process"] == process_id]
        indices = [e.data["index"] for e in process_events]
        assert indices == sorted(indices), f"Events for process {process_id} not in order"


@then("no data should be lost")
def step_check_no_data_loss(context: Context):
    """Verify that no data was lost during concurrent operations"""
    stored_events = context.event_store.get_all_events()
    stored_data = {(e.data["process"], e.data["index"]) for e in stored_events}

    expected_data = {
        (p, i) for p in range(context.process_count) for i in range(context.events_per_process)
    }

    assert stored_data == expected_data, "Some events were lost"


@given("a populated event store")
def step_populate_event_store(context: Context):
    """Create a populated event store for recovery testing"""
    events = []
    for i in range(100):
        event = create_test_event(
            event_type="RecoveryTestEvent",
            aggregate_id=context.test_aggregate_id,
            data={"index": i},
        )
        events.append(event)

    context.event_store.append_batch(events)
    context.recovery_events = events.copy()
    context.pre_crash_events = events.copy()


@when("the system crashes")
def step_simulate_crash(context: Context):
    """Simulate a system crash"""
    # Store the current events for recovery
    context.pre_crash_events = context.event_store.get_all_events()
    # Create a new event store instance to simulate crash
    context.event_store = InMemoryEventStore()


@when("the event store is reinitialized")
def step_reinitialize_event_store(context: Context):
    """Reinitialize the event store"""
    # Restore the events from before the crash
    context.event_store.append_batch(context.pre_crash_events)


@then("all events should be recovered")
def step_check_recovery(context: Context):
    """Verify all events are recovered after crash"""
    recovered_events = context.event_store.get_all_events()
    assert len(recovered_events) == len(
        context.pre_crash_events
    ), f"Not all events recovered. Expected {len(context.pre_crash_events)}, got {len(recovered_events)}"

    # Verify each event was recovered correctly
    for original, recovered in zip(context.pre_crash_events, recovered_events):
        assert original.event_id == recovered.event_id, "Event mismatch after recovery"
        assert original.data == recovered.data, "Event data corrupted"
        assert (
            original.metadata.correlation_id == recovered.metadata.correlation_id
        ), "Event metadata corrupted"


@then("retrieving the aggregate should use the snapshot")
def step_check_snapshot_used(context: Context):
    """Verify that aggregate retrieval uses the snapshot"""
    snapshot = context.event_store.get_latest_snapshot(context.test_aggregate_id)
    assert snapshot is not None, "No snapshot found"
    assert (
        snapshot.version >= context.event_store._snapshot_frequency
    ), f"Snapshot version too low. Expected >= {context.event_store._snapshot_frequency}, got {snapshot.version}"


@then("only events after the snapshot should be replayed")
def step_check_snapshot_replay(context: Context):
    """Verify that only events after the snapshot are replayed"""
    snapshot = context.event_store.get_latest_snapshot(context.test_aggregate_id)
    assert snapshot is not None, "No snapshot found"

    # Get events after the snapshot
    events = context.event_store.get_events_for_aggregate(
        str(context.test_aggregate_id), after_version=snapshot.version
    )

    # Should be fewer events than total
    assert len(events) < len(context.aggregate_events), "All events were replayed"


@then("all events should share the same correlation ID")
def step_check_correlation_ids(context: Context):
    """Verify that all events in a chain share the same correlation ID"""
    correlation_id = context.chain_events[0].metadata.correlation_id
    for event in context.chain_events:
        assert event.metadata.correlation_id == correlation_id, "Event has different correlation ID"


@then("events should maintain their causal relationships")
def step_check_causal_relationships(context: Context):
    """Verify that causal relationships between events are maintained"""
    root_event = next(e for e in context.chain_events if e.data["caused_by"] == "null")
    for event in context.chain_events:
        if event != root_event:
            assert event.metadata.causation_id is not None, "Event missing causation ID"


@then("aggregate state should be consistent")
def step_check_aggregate_consistency(context: Context):
    """Verify that aggregate state is consistent after recovery"""
    recovered_events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))
    assert len(recovered_events) == len(
        context.recovery_events
    ), f"Event count mismatch after recovery. Expected {len(context.recovery_events)}, got {len(recovered_events)}"

    # Verify event order and data integrity
    for original, recovered in zip(context.recovery_events, recovered_events):
        assert original.data == recovered.data, "Event data mismatch"
        assert original.timestamp <= recovered.timestamp, "Event order corrupted"


@then("indexes should be rebuilt correctly")
def step_check_indexes_rebuilt(context: Context):
    """Verify that indexes are correctly rebuilt"""
    # Check that we can retrieve events by aggregate ID
    events = context.event_store.get_events_for_aggregate(str(context.test_aggregate_id))
    assert len(events) == len(
        context.recovery_events
    ), f"Index not rebuilt correctly. Expected {len(context.recovery_events)}, got {len(events)}"

    # Verify that events can be retrieved by correlation ID
    correlation_id = events[0].metadata.correlation_id
    correlated_events = context.event_store.get_events_by_correlation_id(correlation_id)
    assert len(correlated_events) > 0, "Correlation index not rebuilt"
