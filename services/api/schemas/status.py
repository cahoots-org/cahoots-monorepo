"""Status response schemas."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Health status of a service."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    message: str = Field(..., description="Status message or error details")


class MetricsSummary(BaseModel):
    """Summary of key system metrics."""

    error_rate: float = Field(..., description="System error rate")
    latency_p95: float = Field(..., description="95th percentile latency in seconds")
    requests_per_minute: float = Field(..., description="Request rate per minute")
    memory_usage: float = Field(..., description="Memory usage percentage")
    cpu_usage: float = Field(..., description="CPU usage percentage")


class ProjectMetrics(BaseModel):
    """Project-related metrics."""

    active_projects: int = Field(..., description="Number of active projects")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    success_rate: float = Field(..., description="Task completion success rate")


class SystemStatusResponse(BaseModel):
    """System status response."""

    services: Dict[str, ServiceHealth] = Field(..., description="Health status of each service")
    metrics: MetricsSummary = Field(..., description="Key system metrics")
    project_metrics: Optional[ProjectMetrics] = Field(
        None, description="Project-related metrics if available"
    )
