# src/models/task.py
"""Task model for managing development tasks."""
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class TaskStatus(Enum):
    """Task status enum."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"

class Task(BaseModel):
    """Task model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task-123",
                "title": "Implement Login",
                "description": "Add user login functionality",
                "requires_ux": True,
                "status": "open",
                "metadata": {}
            }
        }
    )

    id: str
    title: str
    description: str
    requires_ux: bool = False
    status: TaskStatus = TaskStatus.OPEN
    metadata: Dict[str, Any] = {}

    async def _notify_tester(self, event: Dict[str, Any]) -> None:
        """Notify tester when ready for testing."""
        self.metadata['testing'] = {
            'started_at': event.get('timestamp'),
            'assigned_to': event.get('tester'),
            'test_plan': event.get('test_plan', {})
        }
        
    async def _update_metrics(self, event: Dict[str, Any]) -> None:
        """Update task metrics."""
        self.metadata['metrics'] = {
            'completed_at': event.get('timestamp'),
            'duration': event.get('duration'),
            'complexity_score': event.get('complexity', 1)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Create task from dictionary representation."""
        return cls(**data)