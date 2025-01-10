"""Tests for shared utility functions."""
import pytest
import time
from src.utils.shared_utils import TimeUtils, DataUtils, Validator, MetricsCollector

def test_time_utils():
    """Test TimeUtils class."""
    # Test current_timestamp
    timestamp = TimeUtils.current_timestamp()
    assert isinstance(timestamp, float)
    assert timestamp > 0

def test_data_utils():
    """Test DataUtils class."""
    # Test deep_merge
    dict1 = {"a": 1, "b": {"c": 2}}
    dict2 = {"b": {"d": 3}, "e": 4}
    merged = DataUtils.deep_merge(dict1, dict2)
    
    assert merged == {
        "a": 1,
        "b": {"c": 2, "d": 3},
        "e": 4
    }

def test_validator():
    """Test Validator class."""
    validator = Validator()
    
    # Test schema validation
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name"]
    }
    
    valid_data = {"name": "test", "age": 25}
    assert validator.validate_schema(valid_data, schema) is True
    
    # Test invalid data
    invalid_data = {"age": "invalid"}
    with pytest.raises(Exception):
        validator.validate_schema(invalid_data, schema)
    
    # Test custom validation rule
    def is_positive(value):
        return value > 0
    
    validator.add_validation_rule("is_positive", is_positive)
    assert "is_positive" in validator._custom_rules

def test_metrics_collector():
    """Test MetricsCollector class."""
    collector = MetricsCollector()
    
    # Test counter
    collector.increment_counter("requests")
    collector.increment_counter("requests", 2)
    assert collector.get_counter("requests") == 3
    
    # Test gauge
    collector.set_gauge("cpu_usage", 45.5)
    assert collector.get_gauge("cpu_usage") == 45.5
    
    # Test reset
    collector.reset()
    assert collector.get_counter("requests") == 0
    assert collector.get_gauge("cpu_usage") == 0.0
    
    # Test export
    collector.increment_counter("requests")
    collector.set_gauge("cpu_usage", 45.5)
    
    metrics = collector.export()
    assert metrics == {
        "counters": {"requests": 1},
        "gauges": {"cpu_usage": 45.5}
    } 