"""Project models."""
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class ProjectLinks(BaseModel):
    """Project HATEOAS links."""
    self: str = Field(..., description="Link to this project")
    github_repo: str = Field(..., description="Link to GitHub repository")
    monitoring: str = Field(..., description="Link to monitoring dashboard")
    logs: str = Field(..., description="Link to logs dashboard")

class ProjectBase(BaseModel):
    """Base project model."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    agent_config: Dict = Field(
        default_factory=dict,
        description="Agent configuration"
    )
    resource_limits: Dict = Field(
        default_factory=dict,
        description="Resource limits"
    )

class ProjectCreate(ProjectBase):
    """Project creation model."""
    pass

class ProjectUpdate(BaseModel):
    """Project update model."""
    name: Optional[str] = Field(None, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    agent_config: Optional[Dict] = Field(None, description="Agent configuration")
    resource_limits: Optional[Dict] = Field(None, description="Resource limits")

class Project(ProjectBase):
    """Project model."""
    id: UUID = Field(..., description="Project ID")
    organization_id: UUID = Field(..., description="Organization ID")
    status: str = Field(..., description="Project status")
    progress: float = Field(..., description="Project progress")
    links: ProjectLinks = Field(..., description="HATEOAS links")

    class Config:
        """Pydantic config."""
        from_attributes = True 