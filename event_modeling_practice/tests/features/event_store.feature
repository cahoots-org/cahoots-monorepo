Feature: Event Store Management
  As a system developer
  I want to ensure the event store works reliably
  So that event sourcing operations are consistent and durable

  Background:
    Given a clean event store
    And a test aggregate with ID "test-123"

  @core
  Scenario: Store and retrieve events
    When I append an event
      | type           | aggregate_id | data                |
      | TestEventType  | test-123     | {"key": "value"}   |
    Then the event should be stored successfully
    And I should be able to retrieve the event by aggregate ID
    And the event should have correct metadata
      | schema_version | actor_id  | context            |
      | 1             | system    | {"source": "test"} |

  @core
  Scenario: Event versioning and migration
    Given an event with version 1
      | type           | aggregate_id | data                |
      | TestEventType  | test-123     | {"old_field": "x"} |
    When the event schema is migrated to version 2
    Then the event should be retrieved with updated schema
      | new_field     | migrated_from |
      | converted_x   | old_field     |

  @core
  Scenario: Aggregate snapshots
    Given multiple events for an aggregate
      | type           | aggregate_id | data                |
      | TestEventType1 | test-123     | {"count": 1}       |
      | TestEventType2 | test-123     | {"count": 2}       |
    Then a snapshot should be created automatically
    And retrieving the aggregate should use the snapshot
    And only events after the snapshot should be replayed

  @core
  Scenario: Event correlation and causation
    When I create a chain of related events
      | type           | aggregate_id | caused_by |
      | RootEvent     | test-123     | null      |
      | ChildEvent1   | test-123     | RootEvent |
      | ChildEvent2   | test-123     | RootEvent |
    Then all events should share the same correlation ID
    And I can trace the causation chain
    And events should maintain their causal relationships

  Scenario: Batch event operations
    When I append multiple events in a batch
      | type           | aggregate_id | data                |
      | TestEventType1 | test-123     | {"key": "value1"}  |
      | TestEventType2 | test-123     | {"key": "value2"}  |
    Then all events should be stored atomically
    And I should be able to retrieve all events in order
    And events should share the same correlation ID

  Scenario: Compressed event storage
    Given a large number of events
      | count | aggregate_id |
      | 1000  | test-123    |
    When events are stored in batches
    Then the storage size should be optimized
    And retrieval performance should be maintained
    And events should be stored in compressed format

  Scenario: Concurrent event operations
    Given multiple concurrent processes
    When they simultaneously append events
      | process | events_count |
      | 1       | 100         |
      | 2       | 100         |
      | 3       | 100         |
    Then all events should be stored correctly
    And event order should be maintained
    And no data should be lost

  Scenario: Event store recovery
    Given a populated event store
    When the system crashes
    And the event store is reinitialized
    Then all events should be recovered
    And aggregate state should be consistent
    And indexes should be rebuilt correctly 