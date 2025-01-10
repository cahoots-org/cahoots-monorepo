"""Metrics utilities."""
from contextlib import contextmanager
from time import time
from typing import Dict, Generator, Optional
from prometheus_client import Counter, Gauge, Histogram

# Service metrics
SERVICE_REQUEST_COUNTER = Counter(
    "service_request_total",
    "Total number of service requests",
    ["service", "method"]
)

SERVICE_REQUEST_TIME = Histogram(
    "service_request_seconds",
    "Time spent processing service requests",
    ["service", "method"]
)

SERVICE_ERROR_COUNTER = Counter(
    "service_error_total",
    "Total number of service errors",
    ["service", "error_type"]
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Current state of the circuit breaker (0=open, 1=closed)",
    ["service"]
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    ["service"]
)

# Trello specific metrics
TRELLO_REQUEST_TIME = Histogram(
    "trello_request_seconds",
    "Time spent processing Trello API requests",
    ["method", "endpoint"]
)

TRELLO_ERROR_COUNTER = Counter(
    "trello_error_total",
    "Total number of Trello API errors",
    ["error_type"]
)

# Test execution metrics
TEST_EXECUTION_TIME = Histogram(
    "test_execution_seconds",
    "Time spent executing tests",
    ["suite_id", "test_type"]
)

TEST_RESULT_COUNTER = Counter(
    "test_result_total",
    "Total number of test results by status",
    ["suite_id", "test_type", "status"]
)

TEST_QUEUE_SIZE = Gauge(
    "test_queue_size",
    "Current size of test execution queue",
    ["priority"]
)

TEST_RUNNER_STATE = Gauge(
    "test_runner_state",
    "Current state of test runners (count)",
    ["state"]  # idle, running, error
)

class MetricsCollector:
    """Collector for test execution metrics."""
    
    def record_test_run(
        self,
        run_id: str,
        suite_id: str,
        summary: Dict
    ) -> None:
        """Record metrics for a test run.
        
        Args:
            run_id: Test run ID
            suite_id: Test suite ID
            summary: Test run summary
        """
        # Record execution time
        TEST_EXECUTION_TIME.labels(
            suite_id=suite_id,
            test_type="suite"
        ).observe(summary["avg_execution_time"])
        
        # Record results by status
        for status in ["passed", "failed", "errors"]:
            TEST_RESULT_COUNTER.labels(
                suite_id=suite_id,
                test_type="suite",
                status=status
            ).inc(summary[status])
            
    def update_queue_size(self, priority: int, size: int) -> None:
        """Update test queue size metric.
        
        Args:
            priority: Queue priority level
            size: Current queue size
        """
        TEST_QUEUE_SIZE.labels(priority=str(priority)).set(size)
        
    def update_runner_count(self, state: str, count: int) -> None:
        """Update test runner count metric.
        
        Args:
            state: Runner state (idle, running, error)
            count: Number of runners in this state
        """
        TEST_RUNNER_STATE.labels(state=state).set(count)

@contextmanager
def track_time(metric: Histogram, labels: Optional[Dict[str, str]] = None) -> Generator[None, None, None]:
    """Track time spent in a context.
    
    Args:
        metric: Histogram metric to record time in
        labels: Labels to attach to the metric
    """
    start = time()
    try:
        yield
    finally:
        duration = time() - start
        if labels:
            metric.labels(**labels).observe(duration)
        else:
            metric.observe(duration)

__all__ = [
    'SERVICE_REQUEST_COUNTER',
    'SERVICE_REQUEST_TIME',
    'SERVICE_ERROR_COUNTER',
    'CIRCUIT_BREAKER_STATE',
    'CIRCUIT_BREAKER_FAILURES',
    'TRELLO_REQUEST_TIME',
    'TRELLO_ERROR_COUNTER',
    'TEST_EXECUTION_TIME',
    'TEST_RESULT_COUNTER',
    'TEST_QUEUE_SIZE',
    'TEST_RUNNER_STATE',
    'MetricsCollector',
    'track_time'
] 