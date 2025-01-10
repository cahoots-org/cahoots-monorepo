"""Data models for the application."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, field_validator, Field
import uuid


class BaseMessage(BaseModel):
    """Base message model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "msg-123",
                "timestamp": "2024-02-20T12:00:00Z",
                "type": "system",
                "payload": {},
                "retry_count": 0,
                "max_retries": 3
            }
        }
    )
    
    id: str
    timestamp: datetime = datetime.utcnow
    type: str
    payload: Dict = {}
    retry_count: int = 0
    max_retries: int = 3


class SystemMetrics(BaseModel):
    """System metrics data."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cpu_percent": 45.2,
                "memory_percent": 62.8,
                "disk_percent": 78.1,
                "open_file_descriptors": 128
            }
        }
    )
    
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    open_file_descriptors: int


class ServiceHealth(BaseModel):
    """Service health details."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "latency_ms": 42.5,
                "last_check": "2024-02-20T12:00:00Z",
                "details": {"version": "1.0.0"}
            }
        }
    )
    
    status: str
    latency_ms: float
    last_check: datetime
    details: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    uptime: int
    redis_connected: bool
    components: Dict[str, str]
    services: Dict[str, Dict[str, Any]]


class Project(BaseModel):
    """Project model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "AI Chat Bot",
                "description": "An AI-powered chat bot for customer service"
            }
        },
        str_min_length=1,
        str_max_length=100
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    
    @field_validator('name', 'description')
    def validate_string_length(cls, v: str) -> str:
        if len(v) < 1:
            raise ValueError("Field must not be empty")
        if len(v) > 100:
            raise ValueError("Field must not exceed 100 characters")
        return v


class ProjectResponse(BaseModel):
    """Project response model."""
    id: str
    name: str
    description: str
    created_at: str
    status: str


class ProjectsResponse(BaseModel):
    """Projects list response model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 1,
                "page": 1,
                "per_page": 10,
                "projects": [
                    {
                        "id": "project-123",
                        "name": "AI Chat Bot",
                        "description": "An AI-powered chat bot for customer service",
                        "created_at": "2024-02-20T12:00:00Z",
                        "updated_at": "2024-02-20T12:00:00Z",
                        "status": "active"
                    }
                ]
            }
        }
    )
    
    total: int
    page: int = 1
    per_page: int = 10
    projects: List[ProjectResponse] = []


class Task(BaseModel):
    """Task model."""
    model_config = ConfigDict(
        json_schema_extra={
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
        },
        str_min_length=1,
        str_max_length=100
    )
    
    id: str
    project_id: str
    title: str
    description: str
    status: str = "pending"
    created_at: datetime = datetime.utcnow
    updated_at: datetime = datetime.utcnow
    assigned_to: Optional[str] = None
    
    @field_validator('title', 'description')
    def validate_string_length(cls, v: str) -> str:
        if len(v) < 1:
            raise ValueError("Field must not be empty")
        if len(v) > 100:
            raise ValueError("Field must not exceed 100 characters")
        return v


class TaskResponse(BaseModel):
    """Task response model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task-123",
                "project_id": "project-123",
                "title": "Implement feature",
                "description": "Implement new feature",
                "status": "pending",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "assigned_to": "user-123"
            }
        }
    )
    
    id: str
    project_id: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str] = None


class TasksResponse(BaseModel):
    """Tasks list response model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "id": "task-123",
                        "project_id": "project-123",
                        "title": "Implement feature",
                        "description": "Implement new feature",
                        "status": "pending",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "assigned_to": "user-123"
                    }
                ]
            }
        }
    )
    
    tasks: List[TaskResponse] = [] 