"""Health check and monitoring schemas."""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class HealthStatus(str, Enum):
    """System health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class DependencyType(str, Enum):
    """System dependency type enum."""
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL_API = "external_api"
    STORAGE = "storage"
    OTHER = "other"

class DependencyStatus(BaseModel):
    """System dependency status model."""
    name: str = Field(..., description="Name of the dependency")
    type: DependencyType = Field(..., description="Type of the dependency")
    status: HealthStatus = Field(..., description="Current health status")
    last_check: datetime = Field(..., description="Timestamp of last health check")
    latency_ms: float = Field(..., description="Current latency in milliseconds")
    is_critical: bool = Field(..., description="Whether this is a critical dependency")
    message: Optional[str] = Field(None, description="Additional status message")

class DependencyCheckResponse(BaseModel):
    """Response model for dependency health check."""
    overall_status: HealthStatus = Field(..., description="Overall system health status")
    dependencies: List[DependencyStatus] = Field(..., description="Status of all dependencies")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    total_dependencies: int = Field(..., description="Total number of dependencies checked")
    healthy_count: int = Field(..., description="Number of healthy dependencies")
    degraded_count: int = Field(..., description="Number of degraded dependencies")
    unhealthy_count: int = Field(..., description="Number of unhealthy dependencies")

class MetricValue(BaseModel):
    """System metric value model."""
    value: float = Field(..., description="Current metric value")
    unit: str = Field(..., description="Metric unit")
    timestamp: datetime = Field(..., description="Timestamp of the measurement")

class DependencyMetrics(BaseModel):
    """Dependency metrics model."""
    latency: MetricValue = Field(..., description="Latency metrics")
    error_rate: MetricValue = Field(..., description="Error rate metrics")
    throughput: MetricValue = Field(..., description="Throughput metrics")
    saturation: Optional[MetricValue] = Field(None, description="Resource saturation metrics")

class DependencyDetails(BaseModel):
    """Detailed dependency information model."""
    status: DependencyStatus = Field(..., description="Current dependency status")
    metrics: DependencyMetrics = Field(..., description="Current dependency metrics")
    config: Dict[str, Any] = Field(..., description="Dependency configuration")
    version: Optional[str] = Field(None, description="Dependency version if applicable")
    uptime: Optional[float] = Field(None, description="Uptime in seconds if applicable")

class HealthCheckResponse(BaseModel):
    """Response model for system health check."""
    status: HealthStatus = Field(..., description="Overall system health status")
    version: str = Field(..., description="System version")
    uptime: float = Field(..., description="System uptime in seconds")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    dependencies: DependencyCheckResponse = Field(..., description="Dependencies health status")
    metrics: Dict[str, MetricValue] = Field(..., description="System-wide metrics")
    message: Optional[str] = Field(None, description="Additional health status message")

class ServiceStatus(BaseModel):
    """Service status response."""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status (healthy, degraded, down)")
    version: str = Field(..., description="Service version")
    uptime: int = Field(..., description="Service uptime in seconds")
    last_check: int = Field(..., description="Last health check timestamp")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Service-specific metrics")

class MetricsResponse(BaseModel):
    """System metrics response."""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    network_io: Dict[str, int] = Field(..., description="Network IO metrics")
    request_stats: Dict[str, int] = Field(..., description="API request statistics")

class HealthStatus(BaseModel):
    """Overall health status response."""
    status: str = Field(..., description="Overall system status")
    timestamp: int = Field(..., description="Status check timestamp")
    services: List[ServiceStatus] = Field(..., description="Service statuses")
    dependencies: List[DependencyStatus] = Field(..., description="Dependency statuses")
    metrics: MetricsResponse = Field(..., description="System metrics")

class MetricsSummary(BaseModel):
    """Summary of system metrics."""
    total_requests: int = Field(..., description="Total number of requests processed")
    error_rate: float = Field(..., description="Current error rate percentage")
    avg_response_time: float = Field(..., description="Average response time in milliseconds")
    active_connections: int = Field(..., description="Number of active connections")
    resource_usage: Dict[str, float] = Field(..., description="Resource utilization percentages")
    timestamp: datetime = Field(..., description="Timestamp of the summary")

class ResourceMetrics(BaseModel):
    """System resource utilization metrics."""
    cpu_usage: MetricValue = Field(..., description="CPU usage metrics")
    memory_usage: MetricValue = Field(..., description="Memory usage metrics")
    disk_usage: MetricValue = Field(..., description="Disk usage metrics")
    network_rx: MetricValue = Field(..., description="Network receive metrics")
    network_tx: MetricValue = Field(..., description="Network transmit metrics")
    timestamp: datetime = Field(..., description="Timestamp of measurements")

class ServiceMetrics(BaseModel):
    """Individual service metrics."""
    service_name: str = Field(..., description="Name of the service")
    request_count: int = Field(..., description="Total requests handled")
    error_count: int = Field(..., description="Total errors encountered")
    avg_latency: float = Field(..., description="Average latency in milliseconds")
    uptime: float = Field(..., description="Service uptime in seconds")
    resource_usage: ResourceMetrics = Field(..., description="Resource utilization metrics")
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Service-specific metrics")
    timestamp: datetime = Field(..., description="Timestamp of metrics collection") 