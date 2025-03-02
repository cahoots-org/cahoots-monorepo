"""Metrics tracking utilities."""

import logging
import statistics
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricsError(Exception):
    """Base exception for metrics errors."""

    pass


class Counter:
    """Counter metric type."""

    def __init__(self, name: str, description: str = "", labels: Dict[str, str] = None):
        """Initialize counter.

        Args:
            name: Counter name
            description: Counter description
            labels: Counter labels
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.value = 0

    def inc(self, value: int = 1) -> None:
        """Increment counter.

        Args:
            value: Value to increment by
        """
        self.value += value

    def get(self) -> int:
        """Get current value.

        Returns:
            Current counter value
        """
        return self.value

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0


class Gauge:
    """Gauge metric type."""

    def __init__(self, name: str, description: str = "", labels: Dict[str, str] = None):
        """Initialize gauge.

        Args:
            name: Gauge name
            description: Gauge description
            labels: Gauge labels
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.value = 0.0

    def set(self, value: float) -> None:
        """Set gauge value.

        Args:
            value: Value to set
        """
        self.value = float(value)

    def inc(self, value: float = 1.0) -> None:
        """Increment gauge.

        Args:
            value: Value to increment by
        """
        self.value += value

    def dec(self, value: float = 1.0) -> None:
        """Decrement gauge.

        Args:
            value: Value to decrement by
        """
        self.value -= value

    def get(self) -> float:
        """Get current value.

        Returns:
            Current gauge value
        """
        return self.value

    def reset(self) -> None:
        """Reset gauge to zero."""
        self.value = 0.0


class Histogram:
    """Histogram metric type."""

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Dict[str, str] = None,
        buckets: List[float] = None,
    ):
        """Initialize histogram.

        Args:
            name: Histogram name
            description: Histogram description
            labels: Histogram labels
            buckets: Histogram buckets
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.buckets = (
            sorted(buckets)
            if buckets
            else [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        )
        self.values: List[float] = []

    def observe(self, value: float) -> None:
        """Record an observation.

        Args:
            value: Value to record
        """
        self.values.append(value)

    def get_stats(self) -> Dict[str, float]:
        """Get histogram statistics.

        Returns:
            Dict with count, sum, avg, min, max, and percentiles
        """
        if not self.values:
            return {
                "count": 0,
                "sum": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(self.values)
        return {
            "count": len(self.values),
            "sum": sum(self.values),
            "avg": statistics.mean(self.values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": statistics.median(sorted_values),
            "p90": sorted_values[int(len(sorted_values) * 0.9)],
            "p95": sorted_values[int(len(sorted_values) * 0.95)],
            "p99": sorted_values[int(len(sorted_values) * 0.99)],
        }

    def reset(self) -> None:
        """Reset histogram."""
        self.values.clear()


class MetricsCollector:
    """Collector for service metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}

    def counter(self, name: str, description: str = "", labels: Dict[str, str] = None) -> Counter:
        """Get or create counter.

        Args:
            name: Counter name
            description: Counter description
            labels: Counter labels

        Returns:
            Counter instance
        """
        if name not in self.counters:
            self.counters[name] = Counter(name, description, labels)
        return self.counters[name]

    def gauge(self, name: str, description: str = "", labels: Dict[str, str] = None) -> Gauge:
        """Get or create gauge.

        Args:
            name: Gauge name
            description: Gauge description
            labels: Gauge labels

        Returns:
            Gauge instance
        """
        if name not in self.gauges:
            self.gauges[name] = Gauge(name, description, labels)
        return self.gauges[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Dict[str, str] = None,
        buckets: List[float] = None,
    ) -> Histogram:
        """Get or create histogram.

        Args:
            name: Histogram name
            description: Histogram description
            labels: Histogram labels
            buckets: Histogram buckets

        Returns:
            Histogram instance
        """
        if name not in self.histograms:
            self.histograms[name] = Histogram(name, description, labels, buckets)
        return self.histograms[name]

    def collect(self) -> Dict[str, Any]:
        """Collect all metrics.

        Returns:
            Dict of all metrics
        """
        metrics = {}

        # Collect counters
        for name, counter in self.counters.items():
            metrics[name] = {"type": "counter", "value": counter.get(), "labels": counter.labels}

        # Collect gauges
        for name, gauge in self.gauges.items():
            metrics[name] = {"type": "gauge", "value": gauge.get(), "labels": gauge.labels}

        # Collect histograms
        for name, histogram in self.histograms.items():
            metrics[name] = {
                "type": "histogram",
                "stats": histogram.get_stats(),
                "labels": histogram.labels,
            }

        return metrics

    def reset(self) -> None:
        """Reset all metrics."""
        for counter in self.counters.values():
            counter.reset()
        for gauge in self.gauges.values():
            gauge.reset()
        for histogram in self.histograms.values():
            histogram.reset()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector: Global metrics collector
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
