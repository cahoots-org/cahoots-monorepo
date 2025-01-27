"""Tests for timing utilities."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from contextlib import contextmanager

from cahoots_core.utils.metrics.timing import track_time
from cahoots_core.utils.metrics.base import MetricsCollector
from cahoots_core.utils.metrics.observability import ObservabilityManager

@pytest.fixture
def timer_context():
    """Create a context manager mock for timer."""
    timer_mock = MagicMock()
    @contextmanager
    def _timer_context(*args, **kwargs):
        try:
            yield timer_mock
        finally:
            pass
    return _timer_context

@pytest.fixture
def metrics_collector(timer_context):
    """Create mock metrics collector."""
    collector = Mock(spec=MetricsCollector)
    collector.histogram = Mock()
    collector.timer = timer_context
    return collector

@pytest.fixture
def observability_manager():
    """Create mock observability manager."""
    manager = Mock(spec=ObservabilityManager)
    manager.start_trace = Mock(return_value=Mock())
    manager.end_trace = Mock()
    return manager

def test_track_time_sync(timer_context):
    """Test timing decorator on sync function."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context

    @track_time()
    def test_func(metrics):
        return "test"

    result = test_func(metrics)
    assert result == "test"

def test_track_time_with_labels(timer_context):
    """Test timing with labels."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context
    labels = {"service": "test"}

    @track_time(labels=labels)
    def test_func(metrics):
        return "test"

    result = test_func(metrics)
    assert result == "test"

def test_track_time_with_buckets():
    """Test timing with histogram buckets."""
    metrics = Mock(spec=MetricsCollector)
    metrics.histogram = Mock()
    buckets = [0.1, 0.5, 1.0]

    @track_time(buckets=buckets)
    def test_func(metrics):
        return "test"

    result = test_func(metrics)
    assert result == "test"
    assert metrics.histogram.called

def test_track_time_with_template(timer_context):
    """Test timing with metric name template."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context

    @track_time(metric_name_template="process_{category}_{action}")
    def test_func(metrics, category, action):
        return f"{category}-{action}"

    result = test_func(metrics, category="user", action="create")
    assert result == "user-create"

def test_track_time_template_fallback(timer_context):
    """Test timing with invalid template."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context

    @track_time(metric_name_template="process_{invalid}")
    def test_func(metrics):
        return "test"

    result = test_func(metrics)
    assert result == "test"

def test_track_time_with_tracing(timer_context):
    """Test timing with tracing enabled."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context
    obs = Mock(spec=ObservabilityManager)
    trace_ctx = Mock()
    obs.start_trace.return_value = trace_ctx

    @track_time(trace=True)
    def test_func(metrics, observability):
        return "test"

    result = test_func(metrics, obs)
    assert result == "test"
    obs.start_trace.assert_called_once()
    obs.end_trace.assert_called_once_with(trace_ctx)

@pytest.mark.asyncio
async def test_track_time_async(timer_context):
    """Test timing decorator on async function."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context

    @track_time()
    async def test_func(metrics):
        await asyncio.sleep(0)
        return "test"

    result = await test_func(metrics)
    assert result == "test"

@pytest.mark.asyncio
async def test_track_time_async_with_tracing(timer_context):
    """Test timing on async function with tracing."""
    metrics = Mock(spec=MetricsCollector)
    metrics.timer = timer_context
    obs = Mock(spec=ObservabilityManager)
    trace_ctx = Mock()
    obs.start_trace.return_value = trace_ctx

    @track_time(trace=True)
    async def test_func(metrics, observability):
        await asyncio.sleep(0)
        return "test"

    result = await test_func(metrics, obs)
    assert result == "test"
    obs.start_trace.assert_called_once()
    obs.end_trace.assert_called_once_with(trace_ctx)

def test_track_time_no_metrics():
    """Test timing without metrics collector."""
    @track_time()
    def test_func():
        return "test"

    result = test_func()
    assert result == "test"

def test_track_time_nested_metrics(timer_context):
    """Test timing with nested metrics collector."""
    class Service:
        def __init__(self):
            self.metrics = Mock(spec=MetricsCollector)
            self.metrics.timer = timer_context

    service = Service()

    @track_time()
    def test_func(service):
        return "test"

    result = test_func(service)
    assert result == "test"

def test_track_time_nested_observability():
    """Test timing with nested observability manager."""
    class Service:
        def __init__(self):
            self.observability = Mock(spec=ObservabilityManager)
            self.observability.start_trace.return_value = Mock()

    service = Service()

    @track_time(trace=True)
    def test_func(service):
        return "test"

    result = test_func(service)
    assert result == "test"
    assert service.observability.start_trace.called
    assert service.observability.end_trace.called 