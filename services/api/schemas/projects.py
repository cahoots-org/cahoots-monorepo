"""Project API schemas."""
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    agent_config: Dict = Field(default_factory=dict, description="Agent configuration")
    resource_limits: Dict = Field(default_factory=dict, description="Resource limits")

class ProjectCreate(ProjectBase):
    """Project creation schema."""
    organization_id: UUID = Field(..., description="Organization identifier")

class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: Optional[str] = Field(None, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    agent_config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits")

class ProjectResponse(BaseModel):
    """Project response model."""
    id: UUID = Field(..., description="Project identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    organization_id: UUID = Field(..., description="Organization identifier")
    team_id: Optional[UUID] = Field(None, description="Team identifier")
    agent_config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")
    status: str = Field(..., description="Project status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

class ProjectsResponse(BaseModel):
    """Projects list response model."""
    total: int = Field(..., description="Total number of projects")
    projects: List[ProjectResponse] = Field(..., description="List of projects")

    model_config = ConfigDict(from_attributes=True)

class AgentConfig(BaseModel):
    """Agent deployment configuration."""
    agent_type: str = Field(..., description="Type of agent to deploy")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific configuration")

    model_config = ConfigDict(from_attributes=True)

class AgentDeployment(BaseModel):
    """Agent deployment status."""
    agent_type: str = Field(..., description="Type of agent deployed")
    status: str = Field(..., description="Deployment status")

    model_config = ConfigDict(from_attributes=True) 