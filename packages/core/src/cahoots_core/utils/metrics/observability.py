"""Observability module for system monitoring and tracing."""
import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
from .base import MetricsCollector
from .performance import PerformanceAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class TraceContext:
    """Container for trace context."""
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    service_name: str = ""
    operation_name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"
    error: Optional[Exception] = None

class ObservabilityManager:
    """Manager for system observability including metrics, traces and logs."""
    
    def __init__(
        self,
        service_name: str,
        metrics: Optional[MetricsCollector] = None,
        performance: Optional[PerformanceAnalyzer] = None,
        tracer: Optional[trace.Tracer] = None
    ):
        """Initialize observability manager.
        
        Args:
            service_name: Name of the service being monitored
            metrics: Optional metrics collector instance
            performance: Optional performance analyzer instance
            tracer: Optional OpenTelemetry tracer instance
        """
        self.service_name = service_name
        self.metrics = metrics or MetricsCollector(service_name)
        self.performance = performance or PerformanceAnalyzer(
            service_name,
            metrics=self.metrics
        )
        self.tracer = tracer or trace.get_tracer(__name__)
        self.traces: List[TraceContext] = []
        
        # Initialize trace metrics
        self.metrics.gauge("active_traces", 0)
        self.metrics.gauge("completed_traces", 0)
        self.metrics.gauge("failed_traces", 0)
        self.metrics.histogram("trace_duration_ms", 0)
    
    def start_trace(
        self,
        operation_name: str,
        parent_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TraceContext:
        """Start a new trace.
        
        Args:
            operation_name: Name of the operation being traced
            parent_id: Optional ID of parent trace
            attributes: Optional trace attributes
            
        Returns:
            TraceContext for the new trace
        """
        span = self.tracer.start_span(operation_name)
        
        trace_ctx = TraceContext(
            trace_id=format(span.get_span_context().trace_id, "x"),
            span_id=format(span.get_span_context().span_id, "x"),
            parent_id=parent_id,
            service_name=self.service_name,
            operation_name=operation_name,
            attributes=attributes or {}
        )
        
        self.traces.append(trace_ctx)
        self.metrics.gauge("active_traces", len(self.traces))
        
        return trace_ctx
    
    def end_trace(
        self,
        trace_ctx: TraceContext,
        status: str = "OK",
        error: Optional[Exception] = None
    ):
        """End a trace.
        
        Args:
            trace_ctx: The trace context to end
            status: Final trace status
            error: Optional error that occurred
        """
        trace_ctx.end_time = datetime.utcnow()
        trace_ctx.duration = (
            trace_ctx.end_time - trace_ctx.start_time
        ).total_seconds() * 1000
        trace_ctx.status = status
        trace_ctx.error = error
        
        # Update metrics
        self.metrics.histogram("trace_duration_ms", trace_ctx.duration)
        self.metrics.gauge("active_traces", len(self.traces))
        if status == "OK":
            self.metrics.counter("completed_traces")
        else:
            self.metrics.counter("failed_traces")
            
        # Log completion
        log_msg = (
            f"Trace completed: {trace_ctx.operation_name} "
            f"(duration: {trace_ctx.duration:.2f}ms)"
        )
        if error:
            logger.error(
                f"{log_msg} with error: {str(error)}\n"
                f"{traceback.format_exc()}"
            )
        else:
            logger.info(log_msg)
    
    def add_trace_event(
        self,
        trace_ctx: TraceContext,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Add an event to a trace.
        
        Args:
            trace_ctx: The trace context to add event to
            event_name: Name of the event
            attributes: Optional event attributes
        """
        event = {
            "name": event_name,
            "timestamp": datetime.utcnow(),
            "attributes": attributes or {}
        }
        trace_ctx.events.append(event)
    
    def get_active_traces(self) -> List[TraceContext]:
        """Get all active traces.
        
        Returns:
            List of active trace contexts
        """
        return [t for t in self.traces if not t.end_time]
    
    def get_completed_traces(
        self,
        window: Optional[timedelta] = None
    ) -> List[TraceContext]:
        """Get completed traces within time window.
        
        Args:
            window: Optional time window to filter traces
            
        Returns:
            List of completed trace contexts
        """
        completed = [t for t in self.traces if t.end_time]
        if not window:
            return completed
            
        cutoff = datetime.utcnow() - window
        return [t for t in completed if t.end_time >= cutoff]
    
    def get_failed_traces(
        self,
        window: Optional[timedelta] = None
    ) -> List[TraceContext]:
        """Get failed traces within time window.
        
        Args:
            window: Optional time window to filter traces
            
        Returns:
            List of failed trace contexts
        """
        failed = [t for t in self.traces if t.error]
        if not window:
            return failed
            
        cutoff = datetime.utcnow() - window
        return [t for t in failed if t.end_time >= cutoff]
    
    @contextmanager
    def trace(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracing code blocks.
        
        Args:
            operation_name: Name of the operation to trace
            attributes: Optional trace attributes
            
        Yields:
            TraceContext for the trace
        """
        trace_ctx = self.start_trace(operation_name, attributes=attributes)
        try:
            yield trace_ctx
            self.end_trace(trace_ctx)
        except Exception as e:
            self.end_trace(trace_ctx, status="ERROR", error=e)
            raise
    
    def traced(
        self,
        operation_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Callable:
        """Decorator for tracing functions.
        
        Args:
            operation_name: Optional name of operation (defaults to function name)
            attributes: Optional trace attributes
            
        Returns:
            Decorated function with tracing
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__
                with self.trace(op_name, attributes) as trace_ctx:
                    return await func(*args, **kwargs)
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__
                with self.trace(op_name, attributes) as trace_ctx:
                    return func(*args, **kwargs)
                    
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def reset(self):
        """Reset collected traces."""
        self.traces.clear()
        self.metrics.reset()
        self.performance.reset() 