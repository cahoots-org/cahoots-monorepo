"""Epic model for organizing user stories into major functional areas."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class EpicStatus(str, Enum):
    """Epic status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Epic(BaseModel):
    """Represents a major functional area of the system."""

    id: str = Field(..., description="Unique Epic ID (e.g., EP-1)")
    title: str = Field(..., description="Short, descriptive title")
    description: str = Field(..., description="What this epic covers")
    scope_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords to help classify stories to this epic"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Priority level (1=highest, 5=lowest)"
    )
    status: EpicStatus = Field(default=EpicStatus.ACTIVE)
    root_task_id: str = Field(..., description="ID of the root task this epic belongs to")

    # Story tracking
    story_ids: List[str] = Field(
        default_factory=list,
        description="IDs of user stories in this epic"
    )
    story_count: int = Field(default=0, description="Total number of stories")
    completed_story_count: int = Field(default=0, description="Number of completed stories")

    # Coverage metrics
    coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well this epic covers its intended scope"
    )
    has_gaps: bool = Field(
        default=False,
        description="Whether gaps have been detected in this epic"
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_story(self, story_id: str) -> None:
        """Add a story to this epic."""
        if story_id not in self.story_ids:
            self.story_ids.append(story_id)
            self.story_count = len(self.story_ids)
            self.updated_at = datetime.now(timezone.utc)

    def remove_story(self, story_id: str) -> None:
        """Remove a story from this epic."""
        if story_id in self.story_ids:
            self.story_ids.remove(story_id)
            self.story_count = len(self.story_ids)
            self.updated_at = datetime.now(timezone.utc)

    def calculate_completion_percentage(self) -> float:
        """Calculate the completion percentage based on stories."""
        if self.story_count == 0:
            return 0.0
        return (self.completed_story_count / self.story_count) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: dict) -> "Epic":
        """Create from dictionary."""
        return cls(**data)


class EpicGeneration(BaseModel):
    """Result of epic generation from a root task."""

    epics: List[Epic] = Field(..., description="Generated epics")
    coverage_analysis: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="Analysis of how well epics cover the root task"
    )
    generation_reasoning: str = Field(
        default="",
        description="Reasoning for epic breakdown"
    )
    suggested_priority_order: List[str] = Field(
        default_factory=list,
        description="Suggested order of epic IDs by priority"
    )