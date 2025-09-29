"""Request models for API endpoints."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TechPreferences(BaseModel):
    """Tech stack preferences for task decomposition."""
    application_type: Optional[str] = Field(None, description="Type of application (e.g., 'web-application', 'mobile-application')")
    tech_stack_id: Optional[str] = Field(None, description="Specific tech stack ID (e.g., 'react-node-postgres')")
    github_repo: Optional[str] = Field(None, description="GitHub repository URL for context")
    additional_requirements: Optional[str] = Field(None, description="Additional technical requirements")
    preferred_languages: Optional[list[str]] = Field(default_factory=list, description="Preferred programming languages")
    frameworks: Optional[Dict[str, str]] = Field(default_factory=dict, description="Preferred frameworks by category")
    deployment_target: Optional[str] = Field(None, description="Deployment target (e.g., 'aws', 'gcp', 'on-premise')")


class RepositoryInfo(BaseModel):
    """Repository information for context."""
    type: str = Field(..., description="Repository type: 'github', 'custom', or 'url'")
    url: str = Field(..., description="Repository URL")
    branch: str = Field("main", description="Branch to analyze")
    name: Optional[str] = Field(None, description="Repository name")
    repo_id: Optional[str] = Field(None, description="Repository ID (for GitHub repos)")

    @field_validator("type")
    def validate_type(cls, v):
        """Ensure repository type is valid."""
        valid_types = {"github", "custom", "url"}
        if v not in valid_types:
            raise ValueError(f"Repository type must be one of: {', '.join(valid_types)}")
        return v


class TaskRequest(BaseModel):
    """Request model for task creation and processing."""
    description: str = Field(..., min_length=1, max_length=5000, description="Description of the task")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum recursion depth for decomposition")
    max_subtasks: int = Field(7, ge=1, le=20, description="Maximum number of subtasks per task")
    complexity_threshold: float = Field(0.45, ge=0.1, le=0.9, description="Threshold for determining task atomicity")
    tech_preferences: Optional[TechPreferences] = Field(None, description="User's tech stack preferences")
    requires_approval: bool = Field(False, description="Whether to pause for approval after decomposition")
    repository: Optional[RepositoryInfo] = Field(None, description="Repository information for context")
    user_id: Optional[str] = Field(None, description="ID of the user creating the task")

    # Optimization settings
    use_cache: bool = Field(True, description="Whether to use caching for similar tasks")
    use_templates: bool = Field(True, description="Whether to use templates for common patterns")
    batch_siblings: bool = Field(True, description="Whether to batch process sibling tasks")

    @field_validator("description")
    def validate_description(cls, v):
        """Ensure description is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("Description cannot be empty or just whitespace")
        return v.strip()


class TaskUpdateRequest(BaseModel):
    """Request model for updating an existing task."""
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[str] = Field(None, description="New status for the task")
    implementation_details: Optional[str] = Field(None, description="Technical implementation details")
    story_points: Optional[int] = Field(None, ge=1, le=21, description="Story points estimate")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection if applicable")

    @field_validator("status")
    def validate_status(cls, v):
        """Ensure status is valid."""
        if v is not None:
            valid_statuses = {"submitted", "processing", "in_progress", "completed", "error", "awaiting_approval", "rejected"}
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v