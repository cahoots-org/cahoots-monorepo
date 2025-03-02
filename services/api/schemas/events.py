"""Project event schemas."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    """Schema for creating a new project event."""

    event_type: str = Field(..., description="Type of project event")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    version_vector: Dict[str, int] = Field(
        default={"master": 0}, description="Version vector for optimistic concurrency control"
    )

    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    """Response schema for project events."""

    id: UUID = Field(..., description="Event identifier")
    project_id: UUID = Field(..., description="Project identifier")
    event_type: str = Field(..., description="Type of project event")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    timestamp: datetime = Field(..., description="Event timestamp")
    version: int = Field(..., description="Event version")
    version_vector: Dict[str, int] = Field(..., description="Version vector")

    model_config = ConfigDict(from_attributes=True)
