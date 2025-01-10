"""Tests for metrics utilities."""
import pytest
from unittest.mock import patch
from prometheus_client import REGISTRY

from src.utils.metrics import (
    MetricsCollector,
    TEST_EXECUTION_TIME,
    TEST_RESULT_COUNTER,
    TEST_QUEUE_SIZE,
    TEST_RUNNER_STATE,
    track_time
)

@pytest.fixture
def metrics_collector():
    """Create metrics collector instance."""
    return MetricsCollector()

@pytest.fixture
def sample_summary():
    """Create sample test run summary."""
    return {
        "total": 10,
        "passed": 7,
        "failed": 2,
        "errors": 1,
        "pass_rate": 0.7,
        "avg_execution_time": 1.5
    }

def test_update_queue_size(metrics_collector):
    """Test updating queue size metrics."""
    # Set queue sizes
    metrics_collector.update_queue_size(0, 5)  # Priority 0
    metrics_collector.update_queue_size(1, 3)  # Priority 1
    
    # Verify gauge values
    assert get_gauge_value(TEST_QUEUE_SIZE, {"priority": "0"}) == 5
    assert get_gauge_value(TEST_QUEUE_SIZE, {"priority": "1"}) == 3
    
    # Update values
    metrics_collector.update_queue_size(0, 2)
    metrics_collector.update_queue_size(1, 0)
    
    # Verify updated values
    assert get_gauge_value(TEST_QUEUE_SIZE, {"priority": "0"}) == 2
    assert get_gauge_value(TEST_QUEUE_SIZE, {"priority": "1"}) == 0

def test_update_runner_count(metrics_collector):
    """Test updating runner count metrics."""
    # Set initial counts
    metrics_collector.update_runner_count("idle", 2)
    metrics_collector.update_runner_count("running", 3)
    metrics_collector.update_runner_count("error", 1)
    
    # Verify gauge values
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "idle"}) == 2
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "running"}) == 3
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "error"}) == 1
    
    # Update values
    metrics_collector.update_runner_count("idle", 4)
    metrics_collector.update_runner_count("running", 1)
    metrics_collector.update_runner_count("error", 0)
    
    # Verify updated values
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "idle"}) == 4
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "running"}) == 1
    assert get_gauge_value(TEST_RUNNER_STATE, {"state": "error"}) == 0

def test_track_time_with_labels():
    """Test time tracking with labels."""
    initial_time = get_histogram_sum(TEST_EXECUTION_TIME, {"suite_id": "test-1", "test_type": "unit"})
    
    with track_time(
        TEST_EXECUTION_TIME,
        {"suite_id": "test-1", "test_type": "unit"}
    ):
        pass  # Simulate work
        
    final_time = get_histogram_sum(TEST_EXECUTION_TIME, {"suite_id": "test-1", "test_type": "unit"})
    assert final_time > initial_time

# Helper functions to get metric values
def get_counter_value(counter, labels):
    """Get current value of a Counter metric."""
    return REGISTRY.get_sample_value(
        counter._name,
        labels=labels
    ) or 0

def get_gauge_value(gauge, labels):
    """Get current value of a Gauge metric."""
    return REGISTRY.get_sample_value(
        gauge._name,
        labels=labels
    ) or 0

def get_histogram_sum(histogram, labels):
    """Get current sum of a Histogram metric."""
    return REGISTRY.get_sample_value(
        f"{histogram._name}_sum",
        labels=labels
    ) or 0 