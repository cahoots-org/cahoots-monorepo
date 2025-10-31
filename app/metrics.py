"""Prometheus metrics for performance monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time
from typing import Callable, Any

# LLM Call Metrics
llm_calls_total = Counter(
    'llm_calls_total',
    'Total number of LLM API calls',
    ['operation', 'model', 'status']
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'Duration of LLM API calls in seconds',
    ['operation', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total tokens used in LLM calls',
    ['operation', 'model', 'type']  # type: prompt or completion
)

# Task Processing Metrics
task_processing_duration = Histogram(
    'task_processing_duration_seconds',
    'Duration of task processing pipeline',
    ['complexity'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Phase-level metrics for decomposition pipeline
epic_story_generation_duration = Histogram(
    'epic_story_generation_duration_seconds',
    'Duration of epic and story generation phase',
    ['task_count_bucket'],  # Label for task count ranges
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

story_decomposition_duration = Histogram(
    'story_decomposition_duration_seconds',
    'Duration of story-to-tasks decomposition phase',
    ['task_count_bucket'],  # Label for task count ranges
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

event_modeling_duration = Histogram(
    'event_modeling_duration_seconds',
    'Duration of event modeling analysis phase',
    ['task_count_bucket'],  # Label for task count ranges
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

context_engine_publish_duration = Histogram(
    'context_engine_publish_duration_seconds',
    'Duration of context engine data publishing',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

tasks_processed_total = Counter(
    'tasks_processed_total',
    'Total tasks processed',
    ['status', 'complexity']
)

# Generation Metrics
epics_generated_total = Counter('epics_generated_total', 'Total epics generated')
stories_generated_total = Counter('stories_generated_total', 'Total stories generated')
impl_tasks_generated_total = Counter('impl_tasks_generated_total', 'Total implementation tasks generated')

# Current state
active_tasks = Gauge('active_tasks', 'Number of tasks currently being processed')


def track_llm_call(operation: str, model: str = "unknown"):
    """Decorator to track LLM call metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                llm_call_duration.labels(operation=operation, model=model).observe(duration)
                llm_calls_total.labels(operation=operation, model=model, status=status).inc()
        return wrapper
    return decorator


def track_task_processing(complexity: str = "unknown"):
    """Decorator to track task processing metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            active_tasks.inc()
            start = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                active_tasks.dec()
                task_processing_duration.labels(complexity=complexity).observe(duration)
                tasks_processed_total.labels(status=status, complexity=complexity).inc()
        return wrapper
    return decorator


def get_task_count_bucket(task_count: int) -> str:
    """Convert task count to a bucket label for metrics."""
    if task_count <= 5:
        return "1-5"
    elif task_count <= 10:
        return "6-10"
    elif task_count <= 20:
        return "11-20"
    elif task_count <= 50:
        return "21-50"
    else:
        return "51+"


def get_metrics():
    """Get current metrics in Prometheus format."""
    return generate_latest()
