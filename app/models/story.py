"""User Story model for capturing user requirements."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class StoryStatus(str, Enum):
    """User story status enumeration."""
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class StoryPriority(str, Enum):
    """Story priority levels."""
    MUST_HAVE = "must_have"
    SHOULD_HAVE = "should_have"
    COULD_HAVE = "could_have"
    WONT_HAVE = "wont_have"


class UserStory(BaseModel):
    """Represents a user story within an epic."""

    id: str = Field(..., description="Unique Story ID (e.g., US-1)")
    epic_id: str = Field(..., description="ID of the parent epic")

    # Story definition (As a... I want... So that...)
    actor: str = Field(..., description="User role/persona")
    action: str = Field(..., description="What they want to do")
    benefit: str = Field(..., description="Why they want it")

    # Acceptance criteria
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of acceptance criteria"
    )

    # Story metadata
    status: StoryStatus = Field(default=StoryStatus.DRAFT)
    priority: StoryPriority = Field(default=StoryPriority.SHOULD_HAVE)
    story_points: Optional[int] = Field(
        default=None,
        ge=1,
        le=21,
        description="Estimated story points"
    )

    # Task tracking
    task_ids: List[str] = Field(
        default_factory=list,
        description="IDs of tasks implementing this story"
    )
    completed_task_count: int = Field(default=0)

    # Discovery metadata
    discovered_at_depth: int = Field(
        default=0,
        description="Depth in task tree where story was discovered"
    )
    is_gap_filler: bool = Field(
        default=False,
        description="True if discovered due to coverage gap"
    )
    discovered_from_task_id: Optional[str] = Field(
        default=None,
        description="Task that triggered story discovery"
    )

    # Classification confidence
    epic_classification_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in epic assignment"
    )
    needs_epic_review: bool = Field(
        default=False,
        description="True if epic assignment needs manual review"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_full_story_text(self) -> str:
        """Get the full story text in standard format."""
        return f"As a {self.actor}, I want to {self.action}, so that {self.benefit}"

    def add_task(self, task_id: str) -> None:
        """Add a task to this story."""
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self.updated_at = datetime.now(timezone.utc)

    def mark_task_completed(self) -> None:
        """Increment completed task count."""
        self.completed_task_count += 1
        if self.completed_task_count >= len(self.task_ids) and self.task_ids:
            self.status = StoryStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def calculate_completion_percentage(self) -> float:
        """Calculate completion percentage based on tasks."""
        if not self.task_ids:
            return 0.0
        return (self.completed_task_count / len(self.task_ids)) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: dict) -> "UserStory":
        """Create from dictionary."""
        return cls(**data)


class StoryGeneration(BaseModel):
    """Result of story generation for an epic or gap."""

    stories: List[UserStory] = Field(..., description="Generated stories")
    generation_context: str = Field(
        default="",
        description="Context that triggered generation (initial/gap)"
    )
    coverage_before: float = Field(
        default=0.0,
        description="Coverage score before generation"
    )
    coverage_after: float = Field(
        default=0.0,
        description="Coverage score after generation"
    )
    reasoning: str = Field(
        default="",
        description="Reasoning for story generation"
    )