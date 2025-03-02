# src/models/task.py
"""Task model for managing development tasks."""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskPriority(Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Task status enum."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"


class Task(BaseModel):
    """A task that needs to be implemented."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task-123",
                "title": "Implement Login",
                "description": "Add user login functionality",
                "requires_ux": True,
                "priority": "medium",
                "status": "open",
                "metadata": {},
            }
        }
    )

    id: str = Field(description="Unique identifier for the task")
    title: str = Field(description="Title of the task")
    description: Optional[str] = Field(default="", description="Detailed description of the task")
    requires_ux: bool = Field(default=False, description="Whether this task requires UX work")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Priority of the task")
    status: TaskStatus = Field(default=TaskStatus.OPEN, description="Current status of the task")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the task"
    )

    @field_validator("title")
    def title_not_empty(cls, v: str) -> str:
        """Validate that title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("description")
    def description_not_none(cls, v: Optional[str]) -> str:
        """Convert None description to empty string."""
        return v if v is not None else ""

    def notify_testers(self) -> None:
        """Notify testers that this task needs testing."""
        pass

    def update_metrics(self) -> None:
        """Update metrics for this task."""
        pass

    def model_dump(self) -> Dict[str, Any]:
        """Convert task to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requires_ux": self.requires_ux,
            "priority": self.priority.value,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    async def _notify_tester(self, event: Dict[str, Any]) -> None:
        """Notify tester when ready for testing."""
        self.metadata["testing"] = {
            "started_at": event.get("timestamp"),
            "assigned_to": event.get("tester"),
            "test_plan": event.get("test_plan", {}),
        }

    async def _update_metrics(self, event: Dict[str, Any]) -> None:
        """Update task metrics."""
        self.metadata["metrics"] = {
            "completed_at": event.get("timestamp"),
            "duration": event.get("duration"),
            "complexity_score": event.get("complexity", 1),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create task from dictionary representation."""
        if isinstance(data.get("priority"), str):
            data["priority"] = TaskPriority(data["priority"])
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        return cls(**data)
