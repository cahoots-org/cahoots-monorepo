from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Optional
from functools import wraps
import time
from fastapi import Request

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

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"]
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total number of rate limit exceeded events",
    ["identifier_type"]  # "api_key" or "ip"
)

rate_limit_remaining = Histogram(
    "rate_limit_remaining",
    "Number of remaining requests before rate limit",
    ["identifier_type"]
)

# Trello metrics
TRELLO_REQUEST_TIME = Histogram(
    'trello_request_duration_seconds',
    'Time spent processing Trello API requests',
    ['method', 'endpoint']
)

TRELLO_ERROR_COUNTER = Counter(
    'trello_errors_total',
    'Number of Trello API errors',
    ['method', 'endpoint', 'status_code']
)

def track_time(metric: Histogram, labels: Optional[Dict[str, str]] = None):
    """Decorator to track execution time of a function"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator 

def track_request_metrics(request: Request) -> None:
    """
    Track request metrics.
    
    Args:
        request: FastAPI request object
    """
    # Track request count and duration
    method = request.method
    path = request.url.path
    status = getattr(request.state, "status_code", 500)
    
    http_requests_total.labels(
        method=method,
        path=path,
        status=status
    ).inc()
    
    # Track request duration if start time was set
    if hasattr(request.state, "start_time"):
        duration = time.time() - request.state.start_time
        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration)
    
    # Track rate limit metrics if available
    if hasattr(request.state, "rate_limit_info"):
        info = request.state.rate_limit_info
        identifier_type = "api_key" if "api_key:" in info.get("key", "") else "ip"
        
        # Track remaining requests
        rate_limit_remaining.labels(
            identifier_type=identifier_type
        ).observe(info["remaining"])

def track_rate_limit_exceeded(identifier_type: str) -> None:
    """
    Track rate limit exceeded event.
    
    Args:
        identifier_type: Type of identifier ("api_key" or "ip")
    """
    rate_limit_exceeded_total.labels(
        identifier_type=identifier_type
    ).inc() 