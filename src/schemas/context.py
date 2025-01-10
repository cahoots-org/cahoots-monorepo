from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ContextEventCreate(BaseModel):
    """Schema for creating a new context event."""
    event_type: str = Field(..., description="Type of the context event")
    event_data: Dict = Field(..., description="Data associated with the event")
    version_vector: Optional[Dict[str, int]] = Field(None, description="Optional version vector for concurrency control")

class ContextEventResponse(BaseModel):
    """Schema for context event response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    event_type: str
    event_data: Dict
    timestamp: datetime
    version_vector: Dict[str, int]

class ContextResponse(BaseModel):
    """Schema for context response."""
    context: Dict = Field(..., description="Current context state")
    version_vector: Dict[str, int] = Field(..., description="Current version vector")

class VersionVectorResponse(BaseModel):
    """Schema for version vector response."""
    version_vector: Dict[str, int] = Field(..., description="Current version vector")
    timestamp: datetime = Field(..., description="Timestamp of the version vector") 