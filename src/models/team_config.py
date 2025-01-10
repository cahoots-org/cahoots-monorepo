from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class ServiceRole(str, Enum):
    DEVELOPER = "developer"
    QA_TESTER = "qa_tester"
    UX_DESIGNER = "ux_designer"
    PROJECT_MANAGER = "project_manager"

class ServiceTier(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class RoleConfig(BaseModel):
    """Configuration for a specific role in the team."""
    enabled: bool = Field(default=True, description="Whether this role is enabled")
    instances: int = Field(default=1, ge=1, le=10, description="Number of instances for this role")
    tier: ServiceTier = Field(default=ServiceTier.STANDARD, description="Service tier for this role")
    context_priority: int = Field(default=1, ge=1, le=10, description="Priority for context allocation")
    context_retention_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="How long to retain role-specific context in hours"
    )
    max_concurrent_tasks: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent tasks this role can handle"
    )
    capabilities: Dict[str, bool] = Field(
        default_factory=lambda: {},
        description="Feature flags for role-specific capabilities"
    )
    
    @field_validator("instances")
    @classmethod
    def validate_instances(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Must have at least 1 instance")
        if v > 10:
            raise ValueError("Cannot exceed 10 instances per role")
        return v

class TeamConfig(BaseModel):
    """Configuration for the entire AI development team."""
    project_id: str = Field(..., description="Unique identifier for the project")
    roles: Dict[ServiceRole, RoleConfig] = Field(
        default_factory=lambda: {
            ServiceRole.DEVELOPER: RoleConfig(instances=2),
            ServiceRole.QA_TESTER: RoleConfig(),
            ServiceRole.UX_DESIGNER: RoleConfig(),
            ServiceRole.PROJECT_MANAGER: RoleConfig(),
        }
    )
    max_total_instances: int = Field(default=10, description="Maximum total instances across all roles")
    context_limit_mb: int = Field(default=100, description="Maximum context size in MB")
    context_sharing_enabled: bool = Field(
        default=True,
        description="Whether roles can share context with each other"
    )
    event_retention_days: int = Field(
        default=30,
        description="How long to retain team events in days"
    )
    
    @field_validator("max_total_instances")
    @classmethod
    def validate_max_total_instances(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Maximum total instances must be at least 1")
        return v
    
    @model_validator(mode='after')
    def validate_total_instances(self) -> 'TeamConfig':
        total = sum(role.instances for role in self.roles.values())
        if total > self.max_total_instances:
            raise ValueError(f"Total instances ({total}) exceeds maximum allowed ({self.max_total_instances})")
        return self

class ProjectLimits(BaseModel):
    max_roles: int = Field(default=10, description="Maximum number of roles allowed")
    max_instances_per_role: int = Field(default=10, description="Maximum instances per role")
    max_total_instances: int = Field(default=20, description="Maximum total instances across all roles")
    max_context_mb: int = Field(default=1000, description="Maximum context size in MB")
    allowed_roles: list[ServiceRole] = Field(default_factory=lambda: list(ServiceRole))
    allowed_tiers: list[ServiceTier] = Field(default_factory=lambda: list(ServiceTier)) 