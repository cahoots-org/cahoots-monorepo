# src/models/story.py
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class StoryPriority(Enum):
    """Story priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StoryStatus(Enum):
    """Story status enum."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"


class Story(BaseModel):
    """A user story that needs to be implemented."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "story-123",
                "title": "User Authentication",
                "description": "Implement user authentication system",
                "priority": "medium",
                "status": "open",
                "metadata": {},
            }
        }
    )

    id: str = Field(description="Unique identifier for the story")
    title: str = Field(description="Title of the story")
    description: str = Field(description="Detailed description of the story")
    priority: StoryPriority = Field(
        default=StoryPriority.MEDIUM, description="Priority of the story"
    )
    status: StoryStatus = Field(default=StoryStatus.OPEN, description="Current status of the story")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the story"
    )

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Optional[Any] = None,
        exclude: Optional[Any] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> Dict[str, Any]:
        """Convert story to dictionary format.

        Args:
            mode: Output mode. Either 'json' or 'python'.
            include: Fields to include in output
            exclude: Fields to exclude from output
            by_alias: Whether to use alias names
            exclude_unset: Whether to exclude unset fields
            exclude_defaults: Whether to exclude fields with default values
            exclude_none: Whether to exclude fields with None values
            round_trip: Whether to include information for converting back to model
            warnings: Whether to emit warnings

        Returns:
            Dictionary representation of the story
        """
        base_dict = super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )

        # Convert enums to strings
        if "priority" in base_dict and isinstance(base_dict["priority"], StoryPriority):
            base_dict["priority"] = base_dict["priority"].value
        if "status" in base_dict and isinstance(base_dict["status"], StoryStatus):
            base_dict["status"] = base_dict["status"].value

        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Story":
        """Create a Story instance from a dictionary."""
        if isinstance(data.get("priority"), str):
            data["priority"] = StoryPriority(data["priority"])
        if isinstance(data.get("status"), str):
            data["status"] = StoryStatus(data["status"])
        return cls(**data)

    def __str__(self) -> str:
        """Return string representation of the story."""
        return f"{self.title} ({self.id})"
