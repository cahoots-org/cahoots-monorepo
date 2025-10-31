"""Performance monitoring utilities."""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TimingMetrics:
    """Track timing metrics for operations."""
    operation: str
    duration: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class PerformanceTracker:
    """Track performance metrics across operations."""

    def __init__(self):
        self.metrics: List[TimingMetrics] = []
        self.operation_totals: Dict[str, List[float]] = defaultdict(list)

    @asynccontextmanager
    async def track(self, operation: str, **metadata):
        """Track timing for an async operation."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            metric = TimingMetrics(
                operation=operation,
                duration=duration,
                metadata=metadata
            )
            self.metrics.append(metric)
            self.operation_totals[operation].append(duration)

            # Log slow operations
            if duration > 5.0:
                logger.warning(
                    f"Slow operation: {operation} took {duration:.2f}s",
                    extra=metadata
                )

    def get_summary(self) -> Dict:
        """Get summary of all tracked metrics."""
        summary = {}
        for op, durations in self.operation_totals.items():
            summary[op] = {
                "count": len(durations),
                "total": sum(durations),
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations)
            }
        return summary

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.operation_totals.clear()


# Global tracker instance
_global_tracker = PerformanceTracker()


def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker."""
    return _global_tracker
