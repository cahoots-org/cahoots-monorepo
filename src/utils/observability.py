"""Observability configuration and utilities."""
from typing import Optional
import os
import time
from contextlib import contextmanager

from ddtrace import tracer, patch
from prometheus_client import Counter, Histogram, Gauge
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import structlog

# Configure structured logging
logger = structlog.get_logger()

# Business KPI Metrics
PROJECT_CREATED = Counter(
    "project_created_total",
    "Total number of projects created",
    labelnames=["type", "language"]
)

TASK_COMPLETED = Counter(
    "task_completed_total",
    "Total number of tasks completed",
    labelnames=["agent_type", "task_type"]
)

CODE_REVIEW_DURATION = Histogram(
    "code_review_duration_seconds",
    "Time taken to complete code reviews",
    labelnames=["agent_type", "project_type"],
    buckets=(30, 60, 120, 300, 600, 1800, 3600)
)

AGENT_TASK_QUEUE = Gauge(
    "agent_task_queue",
    "Number of tasks in agent queue",
    labelnames=["agent_type"]
)

# Trace ID context
REQUEST_ID = "request_id"

@contextmanager
def trace_operation(name: str, attributes: Optional[dict] = None):
    """Context manager for tracing operations with Datadog APM.
    
    Args:
        name: Name of the operation to trace
        attributes: Optional attributes to add to the span
    """
    with tracer.trace(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_tag(key, value)
        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise

def setup_observability(app=None):
    """Configure observability tools including tracing, metrics, and error reporting.
    
    Args:
        app: Optional FastAPI application instance to instrument
    """
    # Set up Datadog APM
    patch(httpx=True, redis=True)  # Automatically instrument libraries
    
    # Configure Sentry
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("ENVIRONMENT", "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[
                FastApiIntegration(),
                RedisIntegration(),
            ],
        )

def track_business_kpi(metric_type: str, **labels):
    """Track business KPI metrics.
    
    Args:
        metric_type: Type of metric to track
        **labels: Labels to attach to the metric
    """
    if metric_type == "project_created":
        PROJECT_CREATED.labels(**labels).inc()
    elif metric_type == "task_completed":
        TASK_COMPLETED.labels(**labels).inc()
    elif metric_type == "code_review":
        duration = labels.pop("duration", 0)
        CODE_REVIEW_DURATION.labels(**labels).observe(duration)
    elif metric_type == "agent_queue":
        value = labels.pop("value", 0)
        AGENT_TASK_QUEUE.labels(**labels).set(value)

@contextmanager
def measure_duration(metric_type: str, **labels):
    """Measure the duration of an operation and record it as a metric.
    
    Args:
        metric_type: Type of metric to track
        **labels: Labels to attach to the metric
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if metric_type == "code_review":
            CODE_REVIEW_DURATION.labels(**labels).observe(duration)

def get_trace_id() -> Optional[str]:
    """Get the current trace ID if available."""
    span = tracer.current_span()
    if span:
        return str(span.trace_id)
    return None 