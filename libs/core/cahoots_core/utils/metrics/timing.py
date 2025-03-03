"""Timing utilities for tracking method execution time."""

import asyncio
import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

from .base import MetricsCollector
from .observability import ObservabilityManager

T = TypeVar("T", bound=Callable[..., Any])


def track_time(
    metric: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    buckets: Optional[list[float]] = None,
    trace: bool = True,
    metric_name_template: Optional[str] = None,
) -> Callable[[T], T]:
    """Decorator to track execution time of methods.

    Args:
        metric: Name of the metric to track. Defaults to function name.
        labels: Additional labels to attach to the metric.
        buckets: Optional histogram buckets for time distribution.
        trace: Whether to create a trace for this operation.
        metric_name_template: Optional template for metric name using function args.
            Example: "process_{category}_{action}" will format using kwargs.

    Returns:
        Decorator function that works with both sync and async functions
    """

    def decorator(func: T) -> T:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get metric name
            metric_name = _get_metric_name(metric or func.__name__, metric_name_template, kwargs)

            # Find metrics collector
            metrics = _find_metrics_collector(args)

            # Find observability manager if tracing enabled
            obs_manager = _find_observability_manager(args) if trace else None

            start_time = time.perf_counter()
            trace_ctx = None

            try:
                if obs_manager:
                    trace_ctx = obs_manager.start_trace(
                        operation_name=metric_name, attributes={**labels} if labels else {}
                    )

                result = await func(*args, **kwargs)
                return result

            finally:
                duration = time.perf_counter() - start_time

                if metrics:
                    if buckets:
                        metrics.histogram(metric_name, duration, labels=labels, buckets=buckets)
                    else:
                        with metrics.timer(metric_name, labels=labels):
                            pass  # Duration already measured

                if trace_ctx:
                    obs_manager.end_trace(trace_ctx)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get metric name
            metric_name = _get_metric_name(metric or func.__name__, metric_name_template, kwargs)

            # Find metrics collector
            metrics = _find_metrics_collector(args)

            # Find observability manager if tracing enabled
            obs_manager = _find_observability_manager(args) if trace else None

            start_time = time.perf_counter()
            trace_ctx = None

            try:
                if obs_manager:
                    trace_ctx = obs_manager.start_trace(
                        operation_name=metric_name, attributes={**labels} if labels else {}
                    )

                result = func(*args, **kwargs)
                return result

            finally:
                duration = time.perf_counter() - start_time

                if metrics:
                    if buckets:
                        metrics.histogram(metric_name, duration, labels=labels, buckets=buckets)
                    else:
                        with metrics.timer(metric_name, labels=labels):
                            pass  # Duration already measured

                if trace_ctx:
                    obs_manager.end_trace(trace_ctx)

        return cast(T, async_wrapper if is_async else sync_wrapper)

    return decorator


def _find_metrics_collector(args: tuple) -> Optional[MetricsCollector]:
    """Find metrics collector in arguments."""
    for arg in args:
        if isinstance(arg, MetricsCollector):
            return arg
        if hasattr(arg, "metrics") and isinstance(arg.metrics, MetricsCollector):
            return arg.metrics
    return None


def _find_observability_manager(args: tuple) -> Optional[ObservabilityManager]:
    """Find observability manager in arguments."""
    for arg in args:
        if isinstance(arg, ObservabilityManager):
            return arg
        if hasattr(arg, "observability") and isinstance(arg.observability, ObservabilityManager):
            return arg.observability
    return None


def _get_metric_name(base_name: str, template: Optional[str], kwargs: Dict[str, Any]) -> str:
    """Get metric name using template if provided."""
    if not template:
        return base_name
    try:
        return template.format(**kwargs)
    except KeyError:
        return base_name  # Fallback to base name if template formatting fails
