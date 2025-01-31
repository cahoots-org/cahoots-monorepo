"""Team schemas."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class TeamBase(BaseModel):
    """Base team schema."""
    name: str
    description: Optional[str] = None
    settings: Dict = Field(default_factory=dict)

class TeamCreate(TeamBase):
    """Team creation schema."""
    pass

class TeamUpdate(TeamBase):
    """Team update schema."""
    name: Optional[str] = None

class TeamMemberBase(BaseModel):
    """Base team member schema."""
    role: str
    permissions: Dict = Field(default_factory=dict)

class TeamMemberAdd(TeamMemberBase):
    """Team member addition schema."""
    user_id: UUID

class TeamMemberUpdate(TeamMemberBase):
    """Team member update schema."""
    role: Optional[str] = None
    permissions: Optional[Dict] = None

class TeamMemberResponse(TeamMemberBase):
    """Team member response schema."""
    id: UUID
    user_id: UUID
    team_id: UUID
    email: str
    full_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamResponse(TeamBase):
    """Team response schema."""
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    members: List[TeamMemberResponse]
    project_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class TeamProjectAssignment(BaseModel):
    """Team project assignment schema."""
    project_id: UUID

class ServiceRole(str, Enum):
    """Available service roles."""
    DEVELOPER = "developer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    ARCHITECT = "architect"
    PM = "project_manager"
    UX = "ux_designer"

class RoleConfig(BaseModel):
    """Configuration for a service role."""
    enabled: bool = Field(True, description="Whether the role is enabled")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Role-specific settings")
    resources: Dict[str, Any] = Field(default_factory=dict, description="Resource limits and requests")

class TeamConfig(BaseModel):
    """Team configuration."""
    roles: Dict[ServiceRole, RoleConfig] = Field(..., description="Role configurations")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Team-wide settings")

class TeamConfigResponse(BaseModel):
    """Response model for team configuration."""
    project_id: str
    config: TeamConfig 

class Team(BaseModel):
    """Team model."""
    id: str
    name: str
    description: Optional[str] = None
    organization_id: str
    
    model_config = ConfigDict(from_attributes=True)

class TeamResponse(BaseModel):
    """Team response model."""
    id: str
    name: str
    description: Optional[str] = None
    organization_id: str
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS links")
    
    model_config = ConfigDict(from_attributes=True)

class TeamsResponse(BaseModel):
    """Teams list response model."""
    total: int = Field(..., description="Total number of teams")
    teams: List[TeamResponse] = Field(..., description="List of teams")
    
    model_config = ConfigDict(from_attributes=True) 