"""Agent metrics models."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResourceMetrics(BaseModel):
    """System resource utilization metrics."""

    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_percent: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    memory_used_mb: float = Field(..., ge=0, description="Memory used in megabytes")
    disk_percent: float = Field(..., ge=0, le=100, description="Disk usage percentage")
    network_rx_bytes: int = Field(..., ge=0, description="Network bytes received")
    network_tx_bytes: int = Field(..., ge=0, description="Network bytes transmitted")


class PerformanceMetrics(BaseModel):
    """Performance-related metrics."""

    avg_response_time_ms: float = Field(
        ..., ge=0, description="Average response time in milliseconds"
    )
    p95_response_time_ms: float = Field(..., ge=0, description="95th percentile response time")
    p99_response_time_ms: float = Field(..., ge=0, description="99th percentile response time")
    requests_per_second: float = Field(..., ge=0, description="Request throughput")
    concurrent_tasks: int = Field(..., ge=0, description="Number of concurrent tasks")


class TaskMetrics(BaseModel):
    """Task processing metrics."""

    tasks_completed: int = Field(..., ge=0, description="Total completed tasks")
    tasks_failed: int = Field(..., ge=0, description="Total failed tasks")
    tasks_pending: int = Field(..., ge=0, description="Tasks in queue")
    success_rate: float = Field(..., ge=0, le=100, description="Task success rate percentage")
    avg_processing_time_ms: float = Field(..., ge=0, description="Average task processing time")
    error_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count of errors by type"
    )


class HealthMetrics(BaseModel):
    """Health status metrics."""

    is_healthy: bool = Field(..., description="Overall health status")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    consecutive_failures: int = Field(..., ge=0, description="Consecutive health check failures")
    warning_count: int = Field(..., ge=0, description="Number of active warnings")
    error_count: int = Field(..., ge=0, description="Number of active errors")


class AgentMetrics(BaseModel):
    """Comprehensive agent metrics."""

    agent_id: str = Field(..., description="Unique identifier for the agent")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics collection timestamp"
    )
    resources: ResourceMetrics = Field(..., description="Resource utilization metrics")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    tasks: TaskMetrics = Field(..., description="Task processing metrics")
    health: HealthMetrics = Field(..., description="Health status metrics")
    custom_metrics: Optional[Dict[str, float]] = Field(
        default=None, description="Custom agent-specific metrics"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class Metric(BaseModel):
    """Metric model."""

    name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
