"""Performance analyzer for monitoring system performance."""
import os
import psutil
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from .base import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """Container for system metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io_counters: Dict[str, int]
    timestamp: datetime = datetime.utcnow()

class PerformanceAnalyzer:
    """Analyzer for system and application performance metrics."""
    
    def __init__(
        self,
        service_name: str,
        metrics: Optional[MetricsCollector] = None,
        sample_interval: int = 60,
        history_size: int = 3600
    ):
        """Initialize performance analyzer.
        
        Args:
            service_name: Name of the service being monitored
            metrics: Optional metrics collector instance
            sample_interval: Interval between samples in seconds
            history_size: Number of samples to keep in history
        """
        self.service_name = service_name
        self.metrics = metrics or MetricsCollector(service_name)
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.system_metrics: List[SystemMetrics] = []
        self._process = psutil.Process(os.getpid())
        
        # Initialize Prometheus metrics
        self.metrics.gauge("system_cpu_percent", 0)
        self.metrics.gauge("system_memory_percent", 0)
        self.metrics.gauge("system_disk_usage_percent", 0)
        self.metrics.gauge("process_cpu_percent", 0)
        self.metrics.gauge("process_memory_percent", 0)
        self.metrics.gauge("process_threads", 0)
        self.metrics.gauge("process_open_files", 0)
        self.metrics.gauge("process_connections", 0)
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics.
        
        Returns:
            SystemMetrics object containing current metrics
        """
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()._asdict()
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io_counters=network
            )
            
            # Update Prometheus metrics
            self.metrics.gauge("system_cpu_percent", cpu_percent)
            self.metrics.gauge("system_memory_percent", memory.percent)
            self.metrics.gauge("system_disk_usage_percent", disk.percent)
            
            # Process metrics
            process_cpu = self._process.cpu_percent()
            process_memory = self._process.memory_percent()
            process_threads = len(self._process.threads())
            process_files = len(self._process.open_files())
            process_connections = len(self._process.connections())
            
            self.metrics.gauge("process_cpu_percent", process_cpu)
            self.metrics.gauge("process_memory_percent", process_memory)
            self.metrics.gauge("process_threads", process_threads)
            self.metrics.gauge("process_open_files", process_files)
            self.metrics.gauge("process_connections", process_connections)
            
            # Store in history
            self.system_metrics.append(metrics)
            if len(self.system_metrics) > self.history_size:
                self.system_metrics.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            raise
    
    def get_metrics_history(
        self,
        window: Optional[timedelta] = None
    ) -> List[SystemMetrics]:
        """Get historical metrics within time window.
        
        Args:
            window: Optional time window to filter metrics
            
        Returns:
            List of SystemMetrics objects within window
        """
        if not window:
            return self.system_metrics
            
        cutoff = datetime.utcnow() - window
        return [m for m in self.system_metrics if m.timestamp >= cutoff]
    
    def get_average_metrics(
        self,
        window: Optional[timedelta] = None
    ) -> Dict[str, float]:
        """Calculate average metrics over time window.
        
        Args:
            window: Optional time window to calculate averages
            
        Returns:
            Dictionary of average metric values
        """
        metrics = self.get_metrics_history(window)
        if not metrics:
            return {}
            
        cpu_values = [m.cpu_percent for m in metrics]
        memory_values = [m.memory_percent for m in metrics]
        disk_values = [m.disk_usage_percent for m in metrics]
        
        return {
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
            "avg_memory_percent": sum(memory_values) / len(memory_values),
            "avg_disk_usage_percent": sum(disk_values) / len(disk_values),
            "samples": len(metrics)
        }
    
    def get_peak_metrics(
        self,
        window: Optional[timedelta] = None
    ) -> Dict[str, float]:
        """Get peak metric values over time window.
        
        Args:
            window: Optional time window to find peaks
            
        Returns:
            Dictionary of peak metric values
        """
        metrics = self.get_metrics_history(window)
        if not metrics:
            return {}
            
        return {
            "peak_cpu_percent": max(m.cpu_percent for m in metrics),
            "peak_memory_percent": max(m.memory_percent for m in metrics),
            "peak_disk_usage_percent": max(m.disk_usage_percent for m in metrics),
            "samples": len(metrics)
        }
    
    def check_thresholds(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        disk_threshold: float = 80.0
    ) -> Dict[str, bool]:
        """Check if current metrics exceed thresholds.
        
        Args:
            cpu_threshold: CPU usage threshold percentage
            memory_threshold: Memory usage threshold percentage
            disk_threshold: Disk usage threshold percentage
            
        Returns:
            Dictionary indicating which metrics exceed thresholds
        """
        if not self.system_metrics:
            return {}
            
        current = self.system_metrics[-1]
        return {
            "cpu_exceeded": current.cpu_percent > cpu_threshold,
            "memory_exceeded": current.memory_percent > memory_threshold,
            "disk_exceeded": current.disk_usage_percent > disk_threshold
        }
    
    def reset(self):
        """Reset collected metrics history."""
        self.system_metrics.clear()
        self.metrics.reset() 