"""Base metrics implementation for performance monitoring."""

import logging
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Value container for metrics with timestamp."""

    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collector for application metrics."""

    def __init__(self, service_name: Optional[str] = None) -> None:
        """Initialize the metrics collector.

        Args:
            service_name: Optional name of the service for metric labels
        """
        self.service_name = service_name or "default"
        self.local_metrics: Dict[str, MetricValue] = {}
        self.prometheus_metrics: Dict[str, Union[Counter, Gauge, Histogram, Summary]] = {}

        # Local metric storage
        self._counters: Dict[str, List[MetricValue]] = {}
        self._gauges: Dict[str, MetricValue] = {}
        self._histograms: Dict[str, List[MetricValue]] = {}
        self._timers: Dict[str, List[float]] = {}

        # Prometheus metrics
        self._prom_counters: Dict[str, Counter] = {}
        self._prom_gauges: Dict[str, Gauge] = {}
        self._prom_histograms: Dict[str, Histogram] = {}
        self._prom_summaries: Dict[str, Summary] = {}

    def _get_metric_name(self, name: str) -> str:
        """Get full metric name with service prefix."""
        return f"{self.service_name}_{name}"

    def counter(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ) -> Counter:
        """Get or create a counter metric.

        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional labels for the metric

        Returns:
            Counter metric
        """
        key = f"counter_{name}"
        if key not in self.prometheus_metrics:
            self.prometheus_metrics[key] = Counter(
                name=name,
                documentation=description,
                labelnames=list(labels.keys()) if labels else [],
            )
        return self.prometheus_metrics[key]

    def gauge(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ) -> Gauge:
        """Get or create a gauge metric.

        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional labels for the metric

        Returns:
            Gauge metric
        """
        key = f"gauge_{name}"
        if key not in self.prometheus_metrics:
            self.prometheus_metrics[key] = Gauge(
                name=name,
                documentation=description,
                labelnames=list(labels.keys()) if labels else [],
            )
        return self.prometheus_metrics[key]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Get or create a histogram metric.

        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional labels for the metric
            buckets: Optional histogram buckets

        Returns:
            Histogram metric
        """
        key = f"histogram_{name}"
        if key not in self.prometheus_metrics:
            self.prometheus_metrics[key] = Histogram(
                name=name,
                documentation=description,
                labelnames=list(labels.keys()) if labels else [],
                buckets=buckets or Histogram.DEFAULT_BUCKETS,
            )
        return self.prometheus_metrics[key]

    def summary(
        self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None
    ) -> Summary:
        """Get or create a summary metric.

        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional labels for the metric

        Returns:
            Summary metric
        """
        key = f"summary_{name}"
        if key not in self.prometheus_metrics:
            self.prometheus_metrics[key] = Summary(
                name=name,
                documentation=description,
                labelnames=list(labels.keys()) if labels else [],
            )
        return self.prometheus_metrics[key]

    def get_metric(self, name: str) -> Optional[MetricValue]:
        """Get a metric value by name.

        Args:
            name: Name of the metric

        Returns:
            Metric value if found, None otherwise
        """
        return self.local_metrics.get(name)

    def get_all_metrics(self) -> Dict[str, MetricValue]:
        """Get all metric values.

        Returns:
            Dictionary of metric values
        """
        return self.local_metrics.copy()

    def counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to increment by
            labels: Optional metric labels
        """
        metric_name = self._get_metric_name(name)

        # Store locally
        if metric_name not in self._counters:
            self._counters[metric_name] = []
        self._counters[metric_name].append(MetricValue(value, labels=labels or {}))

        # Update Prometheus
        if metric_name not in self._prom_counters:
            self._prom_counters[metric_name] = Counter(
                metric_name, f"Counter metric {name}", list(labels.keys()) if labels else []
            )

        if labels:
            self._prom_counters[metric_name].labels(**labels).inc(value)
        else:
            self._prom_counters[metric_name].inc(value)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value.

        Args:
            name: Metric name
            value: Current value
            labels: Optional metric labels
        """
        metric_name = self._get_metric_name(name)

        # Store locally
        self._gauges[metric_name] = MetricValue(value, labels=labels or {})

        # Update Prometheus
        if metric_name not in self._prom_gauges:
            self._prom_gauges[metric_name] = Gauge(
                metric_name, f"Gauge metric {name}", list(labels.keys()) if labels else []
            )

        if labels:
            self._prom_gauges[metric_name].labels(**labels).set(value)
        else:
            self._prom_gauges[metric_name].set(value)

    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name
            value: Observed value
            labels: Optional metric labels
            buckets: Optional custom buckets
        """
        metric_name = self._get_metric_name(name)

        # Store locally
        if metric_name not in self._histograms:
            self._histograms[metric_name] = []
        self._histograms[metric_name].append(MetricValue(value, labels=labels or {}))

        # Update Prometheus
        if metric_name not in self._prom_histograms:
            self._prom_histograms[metric_name] = Histogram(
                metric_name,
                f"Histogram metric {name}",
                list(labels.keys()) if labels else [],
                buckets=buckets,
            )

        if labels:
            self._prom_histograms[metric_name].labels(**labels).observe(value)
        else:
            self._prom_histograms[metric_name].observe(value)

    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Time a block of code.

        Args:
            name: Metric name
            labels: Optional metric labels

        Yields:
            None
        """
        metric_name = self._get_metric_name(name)
        start_time = time.perf_counter()

        try:
            yield
        finally:
            duration = time.perf_counter() - start_time

            # Store locally
            if metric_name not in self._timers:
                self._timers[metric_name] = []
            self._timers[metric_name].append(duration)

            # Update Prometheus
            if metric_name not in self._prom_summaries:
                self._prom_summaries[metric_name] = Summary(
                    metric_name, f"Timer metric {name}", list(labels.keys()) if labels else []
                )

            if labels:
                self._prom_summaries[metric_name].labels(**labels).observe(duration)
            else:
                self._prom_summaries[metric_name].observe(duration)

    def get_counter(self, name: str, window: Optional[timedelta] = None) -> int:
        """Get current counter value.

        Args:
            name: Metric name
            window: Optional time window to sum over

        Returns:
            Current counter value
        """
        metric_name = self._get_metric_name(name)
        if metric_name not in self._counters:
            return 0

        if window:
            cutoff = datetime.utcnow() - window
            values = [v.value for v in self._counters[metric_name] if v.timestamp >= cutoff]
        else:
            values = [v.value for v in self._counters[metric_name]]

        return sum(values)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value.

        Args:
            name: Metric name

        Returns:
            Current gauge value or None if not set
        """
        metric_name = self._get_metric_name(name)
        if metric_name in self._gauges:
            return self._gauges[metric_name].value
        return None

    def get_histogram_stats(
        self, name: str, window: Optional[timedelta] = None
    ) -> Dict[str, float]:
        """Get histogram statistics.

        Args:
            name: Metric name
            window: Optional time window

        Returns:
            Dict with min, max, mean, median and percentiles
        """
        metric_name = self._get_metric_name(name)
        if metric_name not in self._histograms:
            return {}

        if window:
            cutoff = datetime.utcnow() - window
            values = [v.value for v in self._histograms[metric_name] if v.timestamp >= cutoff]
        else:
            values = [v.value for v in self._histograms[metric_name]]

        if not values:
            return {}

        sorted_values = sorted(values)
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": sorted_values[int(len(sorted_values) * 0.95)],
            "p99": sorted_values[int(len(sorted_values) * 0.99)],
        }

    def get_timer_stats(self, name: str, window: Optional[timedelta] = None) -> Dict[str, float]:
        """Get timing statistics.

        Args:
            name: Metric name
            window: Optional time window

        Returns:
            Dict with min, max, mean, median and percentiles
        """
        metric_name = self._get_metric_name(name)
        if metric_name not in self._timers:
            return {}

        values = self._timers[metric_name]
        if not values:
            return {}

        sorted_values = sorted(values)
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": sorted_values[int(len(sorted_values) * 0.95)],
            "p99": sorted_values[int(len(sorted_values) * 0.99)],
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()

        # Reset Prometheus metrics
        for counter in self._prom_counters.values():
            counter._value.set(0)
        for gauge in self._prom_gauges.values():
            gauge._value.set(0)
        self._prom_histograms.clear()
        self._prom_summaries.clear()
