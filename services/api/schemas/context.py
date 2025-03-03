"""Context response schemas."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field


class ContextEventCreate(BaseModel):
    """Schema for creating a new context event."""

    event_type: str = Field(
        ...,
        description="Type of context event (code_change, architectural_decision, standard_update)",
    )
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    version_vector: Dict[str, int] = Field(
        default={"master": 0}, description="Version vector for optimistic concurrency control"
    )


class ContextEventResponse(BaseModel):
    """Response schema for context events."""

    id: UUID
    project_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    version: int
    version_vector: Dict[str, int]


class ContextResponse(BaseModel):
    """Response schema for project context."""

    context: Dict[str, Any] = Field(..., description="Current context state")
    version_vector: Dict[str, int] = Field(..., description="Current version vector")


class VersionVectorResponse(BaseModel):
    """Response schema for version vector."""

    version_vector: Dict[str, int] = Field(..., description="Current version vector")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the version vector"
    )
