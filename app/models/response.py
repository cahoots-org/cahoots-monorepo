"""Response models for API endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .task import Task, TaskStatus


class TaskResponse(BaseModel):
    """Response model for single task operations."""
    task_id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Description of the task")
    status: TaskStatus = Field(..., description="Current status of the task")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    parent_id: Optional[str] = Field(None, description="ID of the parent task")
    children_count: int = Field(0, description="Number of direct child tasks")
    implementation_details: Optional[str] = Field(None, description="Technical implementation details")
    story_points: Optional[int] = Field(None, description="Story points based on task complexity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task context including tech stack")
    user_id: Optional[str] = Field(None, description="ID of the user who created this task")
    is_atomic: bool = Field(False, description="Whether this task is atomic")
    complexity_score: float = Field(0.0, description="Complexity score (0-1)")
    depth: int = Field(0, description="Depth in the task tree")
    rejection_reason: Optional[str] = Field(None, description="Reason why the task was rejected")
    is_rejected: bool = Field(False, description="Whether the task has been rejected")
    rejected_at: Optional[datetime] = Field(None, description="Timestamp when the task was rejected")
    error_message: Optional[str] = Field(None, description="Error message if task processing failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata including extracted events")

    @classmethod
    def from_task(cls, task: Task) -> "TaskResponse":
        """Create response from Task model."""
        return cls(
            task_id=task.id,
            description=task.description,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            parent_id=task.parent_id,
            children_count=len(task.subtasks),
            implementation_details=task.implementation_details,
            story_points=task.story_points,
            context=task.context or {},
            user_id=task.user_id,
            is_atomic=task.is_atomic,
            complexity_score=task.complexity_score,
            depth=task.depth,
            rejection_reason=task.rejection_reason,
            is_rejected=task.is_rejected,
            rejected_at=task.rejected_at,
            error_message=task.error_message,
            metadata=task.metadata or {},
        )


class TaskTreeNode(BaseModel):
    """Hierarchical node for a task tree response."""
    task_id: str
    description: str
    is_atomic: bool = False
    depth: int = 0
    parent_id: Optional[str] = None
    status: TaskStatus = TaskStatus.SUBMITTED
    complexity_score: float = 0.0
    implementation_details: Optional[str] = None
    story_points: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None  # Contains requirements, event model, etc.
    created_at: datetime
    updated_at: datetime
    children: List["TaskTreeNode"] = Field(default_factory=list)

    @classmethod
    def from_task(cls, task: Task, children: List["TaskTreeNode"] = None) -> "TaskTreeNode":
        """Create tree node from Task model."""
        return cls(
            task_id=task.id,
            description=task.description,
            is_atomic=task.is_atomic,
            depth=task.depth,
            parent_id=task.parent_id,
            status=task.status,
            complexity_score=task.complexity_score,
            implementation_details=task.implementation_details,
            story_points=task.story_points,
            context=task.context,
            metadata=task.metadata,  # Include requirements, event model, etc.
            created_at=task.created_at,
            updated_at=task.updated_at,
            children=children or [],
        )


# Enable forward references
TaskTreeNode.model_rebuild()


class TaskTreeResponse(BaseModel):
    """Response model for task tree operations."""
    root: TaskTreeNode = Field(..., description="Root node of the task tree")
    total_tasks: int = Field(..., description="Total number of tasks in the tree")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    atomic_tasks: int = Field(..., description="Number of atomic tasks")
    max_depth: int = Field(..., description="Maximum depth of the tree")
    total_story_points: Optional[int] = Field(None, description="Sum of all story points")
    completion_percentage: float = Field(0.0, description="Percentage of tasks completed")


class TaskStats(BaseModel):
    """Statistics about tasks."""
    total: int = Field(..., description="Total number of tasks")
    completed: int = Field(..., description="Number of completed tasks")
    in_progress: int = Field(..., description="Number of tasks in progress")
    rejected: int = Field(..., description="Number of rejected tasks")
    pending: int = Field(..., description="Number of pending tasks")
    atomic: int = Field(..., description="Number of atomic tasks")
    average_complexity: float = Field(0.0, description="Average complexity score")
    average_depth: float = Field(0.0, description="Average task depth")


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Number of tasks per page")
    stats: Optional[TaskStats] = Field(None, description="Task statistics")