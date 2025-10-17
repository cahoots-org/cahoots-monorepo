"""Core task models for the application."""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import uuid


class TaskStatus(str, Enum):
    """Task processing status."""
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"


class ApproachType(str, Enum):
    """Suggested approach for task processing."""
    DECOMPOSE = "decompose"
    IMPLEMENT = "implement"
    TEMPLATE = "template"
    HUMAN_REVIEW = "human_review"


class Task(BaseModel):
    """Core task model with all necessary fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: TaskStatus = TaskStatus.SUBMITTED
    depth: int = 0
    parent_id: Optional[str] = None
    is_atomic: bool = False
    complexity_score: float = 0.0
    implementation_details: Optional[str] = None
    story_points: Optional[int] = None
    subtasks: List[str] = Field(default_factory=list)  # Just IDs, not full objects
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Additional fields from the original system
    tech_preferences: Optional[Dict[str, Any]] = None
    best_practices: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    is_rejected: bool = False
    rejected_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Epic and Story relationships
    epic_ids: List[str] = Field(
        default_factory=list,
        description="IDs of epics this task belongs to (usually one, but can be multiple for boundary tasks)"
    )
    story_ids: List[str] = Field(
        default_factory=list,
        description="IDs of user stories this task implements"
    )
    coverage_status: str = Field(
        default="pending",
        description="Coverage status: pending, covered, partial, gap"
    )

    @field_validator("depth")
    def validate_depth(cls, v):
        """Ensure depth is non-negative and within limits."""
        if v < 0:
            raise ValueError("Depth must be non-negative")
        if v > 10:  # Maximum depth limit
            raise ValueError("Maximum depth exceeded")
        return v

    @field_validator("complexity_score")
    def validate_complexity(cls, v):
        """Ensure complexity score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Complexity score must be between 0 and 1")
        return v

    @field_validator("story_points")
    def validate_story_points(cls, v):
        """Ensure story points are within valid range."""
        # Convert 0 to None (unestimated)
        if v == 0:
            return None
        if v is not None and not 1 <= v <= 21:
            raise ValueError("Story points must be between 1 and 21")
        return v

    def to_redis_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for Redis storage."""
        data = self.model_dump(mode='json')
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.rejected_at:
            data['rejected_at'] = self.rejected_at.isoformat()
        return data

    @classmethod
    def from_redis_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from Redis dictionary."""
        # Convert ISO format strings back to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'rejected_at' in data and isinstance(data['rejected_at'], str):
            data['rejected_at'] = datetime.fromisoformat(data['rejected_at'])
        return cls(**data)


class TaskAnalysis(BaseModel):
    """Unified task analysis result from a single LLM call."""
    complexity_score: float = Field(..., ge=0, le=1)
    is_atomic: bool
    is_specific: bool
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    suggested_approach: ApproachType
    implementation_hints: Optional[str] = None
    estimated_story_points: Optional[int] = Field(None, ge=1, le=21)
    requires_human_review: bool = False
    similar_patterns: List[str] = Field(default_factory=list)

    # Additional analysis fields
    missing_details: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)

    # Story-driven fields
    story_id: Optional[str] = None
    epic_id: Optional[str] = None


class TaskDecomposition(BaseModel):
    """Result of task decomposition including subtasks with inline details."""
    subtasks: List[Dict[str, Any]]  # Each includes description, is_atomic, implementation_details, etc.
    decomposition_reasoning: str
    estimated_total_points: Optional[int] = None
    suggested_order: Optional[List[int]] = None  # Indices suggesting execution order
    parallel_groups: Optional[List[List[int]]] = None  # Groups of indices that can be done in parallel
    story_id: Optional[str] = None  # Parent story ID for story-driven decomposition
    epic_id: Optional[str] = None  # Parent epic ID for story-driven decomposition

    def get_atomic_tasks(self) -> List[Dict[str, Any]]:
        """Extract only atomic tasks from the decomposition."""
        return [task for task in self.subtasks if task.get('is_atomic', False)]

    def get_complex_tasks(self) -> List[Dict[str, Any]]:
        """Extract only complex (non-atomic) tasks from the decomposition."""
        return [task for task in self.subtasks if not task.get('is_atomic', False)]


class TaskTree(BaseModel):
    """Complete task tree structure."""
    root: Task
    tasks: Dict[str, Task] = Field(default_factory=dict)  # All tasks indexed by ID
    depth_map: Dict[int, List[str]] = Field(default_factory=dict)  # Task IDs by depth level

    def add_task(self, task: Task) -> None:
        """Add a task to the tree."""
        self.tasks[task.id] = task
        if task.depth not in self.depth_map:
            self.depth_map[task.depth] = []
        self.depth_map[task.depth].append(task.id)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_children(self, task_id: str) -> List[Task]:
        """Get all children of a task."""
        task = self.get_task(task_id)
        if not task:
            return []
        return [self.tasks[child_id] for child_id in task.subtasks if child_id in self.tasks]

    def get_all_descendants(self, task_id: str) -> List[Task]:
        """Get all descendants (children, grandchildren, etc.) of a task."""
        descendants = []
        to_process = [task_id]
        while to_process:
            current_id = to_process.pop(0)
            children = self.get_children(current_id)
            descendants.extend(children)
            to_process.extend([child.id for child in children])
        return descendants

    def get_leaf_tasks(self) -> List[Task]:
        """Get all leaf tasks (tasks with no children)."""
        return [task for task in self.tasks.values() if not task.subtasks]

    def get_atomic_tasks(self) -> List[Task]:
        """Get all atomic tasks."""
        return [task for task in self.tasks.values() if task.is_atomic]

    def calculate_completion_percentage(self) -> float:
        """Calculate the percentage of tasks completed."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100