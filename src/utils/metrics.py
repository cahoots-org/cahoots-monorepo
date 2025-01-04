from prometheus_client import Counter, Gauge, Histogram
from typing import Optional, Dict, Any, Generator, Callable, TypeVar, Union
from functools import wraps
import time
from contextlib import contextmanager
from fastapi import Request
import psutil

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'path', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'path'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

# Service-specific metrics
MASTER_DISPATCH_TIME = Histogram(
    'master_dispatch_seconds',
    'Time taken to dispatch tasks to project manager',
    ['task_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

PM_PLANNING_TIME = Histogram(
    'pm_planning_seconds',
    'Time taken for project planning',
    ['project_type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0)
)

DEVELOPER_CODING_TIME = Histogram(
    'developer_coding_seconds',
    'Time taken for coding tasks',
    ['developer_id', 'task_type'],
    buckets=(300, 900, 1800, 3600, 7200)
)

UX_DESIGN_TIME = Histogram(
    'ux_design_seconds',
    'Time taken for UX design tasks',
    ['design_type'],
    buckets=(900, 1800, 3600, 7200, 14400)
)

TEST_EXECUTION_TIME = Histogram(
    'test_execution_seconds',
    'Time taken for test execution',
    ['test_type'],
    buckets=(10, 30, 60, 180, 300)
)

# Inter-service communication metrics
INTERSERVICE_REQUEST_TIME = Histogram(
    'interservice_request_seconds',
    'Time taken for inter-service requests',
    ['source_service', 'target_service', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

INTERSERVICE_ERROR_COUNTER = Counter(
    'interservice_error_total',
    'Total number of inter-service communication errors',
    ['source_service', 'target_service', 'error_type']
)

# Business process metrics
PROJECT_COMPLETION_TIME = Histogram(
    'project_completion_seconds',
    'Time taken to complete entire projects',
    ['project_type', 'complexity'],
    buckets=(3600, 7200, 14400, 28800, 86400)
)

STORY_COMPLETION_TIME = Histogram(
    'story_completion_seconds',
    'Time taken to complete user stories',
    ['story_type', 'priority'],
    buckets=(1800, 3600, 7200, 14400, 28800)
)

CODE_QUALITY_SCORE = Gauge(
    'code_quality_score',
    'Code quality score from automated analysis',
    ['project_id', 'metric_type']
)

TEST_COVERAGE_GAUGE = Gauge(
    'test_coverage_percent',
    'Test coverage percentage',
    ['project_id', 'test_type']
)

# Message metrics
MESSAGE_PUBLISH_COUNTER = Counter(
    'message_publish_total',
    'Total number of messages published',
    ['channel']
)

MESSAGE_PROCESSING_TIME = Histogram(
    'message_processing_seconds',
    'Time spent processing messages',
    ['channel'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

MESSAGE_RETRY_COUNTER = Counter(
    'message_retry_total',
    'Total number of message retries',
    ['channel']
)

MESSAGE_DLQ_COUNTER = Counter(
    'message_dlq_total',
    'Total number of messages sent to DLQ',
    ['channel', 'error_type']
)

MESSAGE_ERROR_COUNTER = Counter(
    'message_error_total',
    'Total number of message processing errors',
    ['channel']
)

# Service metrics
SERVICE_REQUEST_COUNTER = Counter(
    'service_request_total',
    'Total number of service requests',
    ['service', 'method', 'endpoint']
)

SERVICE_REQUEST_TIME = Histogram(
    'service_request_seconds',
    'Time spent on service requests',
    ['service', 'method'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

SERVICE_ERROR_COUNTER = Counter(
    'service_error_total',
    'Total number of service errors',
    ['service', 'error_type']
)

SERVICE_UPTIME = Gauge(
    'service_uptime_seconds',
    'Time since service started in seconds'
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open)',
    ['service']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'circuit_breaker_failures_total',
    'Total number of circuit breaker failures',
    ['service']
)

# Redis metrics
redis_pool_size = Gauge(
    'redis_pool_size',
    'Current number of connections in the Redis connection pool'
)

redis_pool_maxsize = Gauge(
    'redis_pool_maxsize',
    'Maximum number of connections in the Redis connection pool'
)

# Trello metrics
TRELLO_REQUEST_TIME = Histogram(
    "trello_request_seconds",
    "Time spent in Trello API requests",
    ["method", "endpoint"]
)

TRELLO_ERROR_COUNTER = Counter(
    'trello_error_total',
    'Total number of Trello API errors',
    ['method', 'endpoint', 'status_code']
)

GITHUB_REQUEST_TIME = Histogram(
    "github_request_seconds",
    "Time spent on GitHub API requests",
    ["endpoint"]
)

# Type variables for generic function types
F = TypeVar('F', bound=Callable[..., Any])

def track_time(metric: Histogram, labels: Optional[Dict[str, str]] = None) -> Union[Callable[[F], F], Generator[None, None, None]]:
    """Track time spent in a code block or function using a Prometheus histogram.
    
    Can be used as either a decorator or a context manager:
    
    As a decorator:
        @track_time(metric, labels)
        async def my_function():
            ...
            
    As a context manager:
        with track_time(metric, labels):
            ...
    
    Args:
        metric: The histogram metric to update
        labels: Labels to apply to the metric
        
    Returns:
        Union[Callable, Generator]: Either a decorator function or a context manager
    """
    if labels is None:
        labels = {}

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)
        return wrapper  # type: ignore

    # If called with a function, return the decorator
    if callable(metric):
        func, metric = metric, TRELLO_REQUEST_TIME
        return decorator(func)

    # If called without a function, return a context manager
    @contextmanager
    def context_manager() -> Generator[None, None, None]:
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            metric.labels(**labels).observe(duration)

    return context_manager()

def track_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track request metrics.
    
    Args:
        method: HTTP method
        endpoint: Request endpoint
        status_code: Response status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

def track_interservice_request(
    source_service: str,
    target_service: str,
    operation: str,
    duration: float,
    error: Optional[str] = None
):
    """Track inter-service communication metrics.
    
    Args:
        source_service: Service initiating the request
        target_service: Service receiving the request
        operation: Type of operation being performed
        duration: Request duration in seconds
        error: Optional error type if request failed
    """
    INTERSERVICE_REQUEST_TIME.labels(
        source_service=source_service,
        target_service=target_service,
        operation=operation
    ).observe(duration)
    
    if error:
        INTERSERVICE_ERROR_COUNTER.labels(
            source_service=source_service,
            target_service=target_service,
            error_type=error
        ).inc()

def track_project_metrics(
    project_id: str,
    metric_type: str,
    value: float,
    labels: Optional[Dict[str, str]] = None
):
    """Track project-related metrics.
    
    Args:
        project_id: Unique identifier of the project
        metric_type: Type of metric (completion_time, quality_score, test_coverage)
        value: Metric value
        labels: Optional additional labels
    """
    if metric_type == 'completion_time':
        PROJECT_COMPLETION_TIME.labels(**labels).observe(value)
    elif metric_type == 'quality_score':
        CODE_QUALITY_SCORE.labels(
            project_id=project_id,
            metric_type=labels.get('metric_type', 'overall')
        ).set(value)
    elif metric_type == 'test_coverage':
        TEST_COVERAGE_GAUGE.labels(
            project_id=project_id,
            test_type=labels.get('test_type', 'unit')
        ).set(value)

def update_redis_metrics(pool_size: int, max_size: int):
    """Update Redis connection pool metrics.
    
    Args:
        pool_size: Current pool size
        max_size: Maximum pool size
    """
    redis_pool_size.set(pool_size)
    redis_pool_maxsize.set(max_size)

def get_metrics() -> Dict[str, Any]:
    """Get basic system metrics.
    
    Returns:
        Dict[str, Any]: Dictionary containing system metrics like CPU and memory usage.
    """
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "uptime": time.time() - START_TIME
    }

# Initialize start time
START_TIME = time.time() 