import pytest
from datetime import datetime
from src.utils.version_vector import VersionVector

def test_new_version_vector():
    vector = VersionVector.new()
    assert vector.versions == {}
    assert isinstance(vector.timestamp, datetime)

def test_from_json():
    json_str = '{"versions": {"master": 1, "node1": 2}, "timestamp": "2023-01-01T00:00:00"}'
    vector = VersionVector.from_json(json_str)
    assert vector.versions == {"master": 1, "node1": 2}
    assert vector.timestamp == datetime(2023, 1, 1)

def test_from_event():
    class MockEvent:
        version_vector = '{"versions": {"master": 1, "node1": 2}, "timestamp": "2023-01-01T00:00:00"}'
        timestamp = datetime(2023, 1, 1)
    
    event = MockEvent()
    vector = VersionVector.from_event(event)
    assert vector.versions == {"master": 1, "node1": 2}
    # Timestamp is set to current time, not event timestamp

def test_increment():
    vector = VersionVector.new()
    vector.increment("master")
    assert vector.versions == {"master": 1}
    
    vector.increment("node1")
    assert vector.versions == {"master": 1, "node1": 1}
    
    vector.increment("node1")
    assert vector.versions == {"master": 1, "node1": 2}

def test_merge():
    vector1 = VersionVector({"master": 1, "node1": 2})
    vector2 = VersionVector({"master": 2, "node2": 1})
    
    merged = vector1.merge(vector2)
    assert merged.versions == {"master": 2, "node1": 2, "node2": 1}

def test_compatible_with():
    vector1 = VersionVector({"master": 2, "node1": 2})
    vector2 = VersionVector({"master": 1, "node1": 2})
    vector3 = VersionVector({"master": 3, "node1": 1})  # Concurrent with vector1
    
    assert vector1.compatible_with(vector2)  # v1 dominates v2
    assert not vector1.compatible_with(vector3)  # v1 concurrent with v3 (master ahead in v3, node1 ahead in v1)

def test_to_json():
    vector = VersionVector({"master": 1, "node1": 2})
    vector.timestamp = datetime(2023, 1, 1)
    json_str = vector.to_json()
    
    # Recreate vector from JSON to verify
    recreated = VersionVector.from_json(json_str)
    assert recreated.versions == vector.versions
    assert recreated.timestamp == vector.timestamp 