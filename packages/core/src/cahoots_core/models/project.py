"""Project models."""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ProjectBase(BaseModel):
    """Base project model."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    agent_config: Dict = Field(default_factory=dict, description="Agent configuration")
    resource_limits: Dict = Field(default_factory=dict, description="Resource limits")

class ProjectCreate(ProjectBase):
    """Project creation model."""
    pass

class ProjectUpdate(BaseModel):
    """Project update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    agent_config: Optional[Dict] = None
    resource_limits: Optional[Dict] = None

class Project(ProjectBase):
    """Project model."""
    id: UUID = Field(..., description="Project ID")
    organization_id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="active")