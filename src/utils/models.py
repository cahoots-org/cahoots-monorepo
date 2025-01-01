"""Data models for the application."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message model."""
    id: str = Field(..., description="Unique message identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    type: str = Field(..., description="Message type")
    payload: Dict = Field(default_factory=dict, description="Message payload")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")


class SystemMetrics(BaseModel):
    """System resource metrics."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_percent: float = Field(..., description="Disk usage percentage")
    open_file_descriptors: int = Field(..., description="Number of open file descriptors")


class ServiceHealth(BaseModel):
    """Service health details."""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    latency_ms: float = Field(..., description="Service latency in milliseconds")
    last_check: datetime = Field(..., description="Last health check timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall system health status")
    environment: str = Field(..., description="Current environment")
    version: str = Field(..., description="Application version")
    uptime_seconds: int = Field(..., description="Application uptime in seconds")
    system_metrics: SystemMetrics = Field(..., description="System resource metrics")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service health status")
    redis_connected: bool = Field(..., description="Redis connection status")


class Project(BaseModel):
    """Project model."""
    id: str = Field(..., example="project-123", description="Unique project identifier")
    name: str = Field(..., min_length=1, max_length=100, example="My Project", description="Project name")
    description: str = Field(..., min_length=1, example="A new project", description="Project description")

    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "id": "project-123",
                "name": "AI Chat Bot",
                "description": "An AI-powered chat bot for customer service"
            }
        }


class ProjectResponse(BaseModel):
    """Project response model."""
    id: str = Field(..., example="project-123", description="Project identifier")
    name: str = Field(..., example="My Project", description="Project name")
    description: str = Field(..., example="A new project", description="Project description")


class ProjectsResponse(BaseModel):
    """Projects list response model."""
    projects: List[ProjectResponse] = Field(default_factory=list, description="List of projects")


class Task(BaseModel):
    """Task model."""
    id: str = Field(..., example="task-123", description="Unique task identifier")
    project_id: str = Field(..., example="project-123", description="Project identifier")
    title: str = Field(..., min_length=1, max_length=100, example="Implement feature", description="Task title")
    description: str = Field(..., min_length=1, example="Implement new feature", description="Task description")
    status: str = Field(default="pending", example="pending", description="Task status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Task update timestamp")
    assigned_to: Optional[str] = Field(None, example="user-123", description="Assigned user identifier")

    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "id": "task-123",
                "project_id": "project-123",
                "title": "Implement login feature",
                "description": "Implement user authentication and login functionality",
                "status": "pending",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "assigned_to": "user-123"
            }
        }


class TaskResponse(BaseModel):
    """Task response model."""
    id: str = Field(..., example="task-123", description="Task identifier")
    project_id: str = Field(..., example="project-123", description="Project identifier")
    title: str = Field(..., example="Implement feature", description="Task title")
    description: str = Field(..., example="Implement new feature", description="Task description")
    status: str = Field(..., example="pending", description="Task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task update timestamp")
    assigned_to: Optional[str] = Field(None, example="user-123", description="Assigned user identifier")


class TasksResponse(BaseModel):
    """Tasks list response model."""
    tasks: List[TaskResponse] = Field(default_factory=list, description="List of tasks") 