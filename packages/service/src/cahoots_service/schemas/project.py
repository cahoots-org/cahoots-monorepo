"""Project API schemas."""
from typing import Dict, List, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

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

class ProjectResponse(BaseModel):
    """Project response model."""
    id: UUID = Field(..., description="Project identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    organization_id: UUID = Field(..., description="Organization identifier")
    agent_config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS links")

    model_config = ConfigDict(orm_mode=True)

class ProjectsResponse(BaseModel):
    """Projects list response model."""
    total: int = Field(..., description="Total number of projects")
    projects: List[ProjectResponse] = Field(..., description="List of projects")

    model_config = ConfigDict(from_attributes=True) 