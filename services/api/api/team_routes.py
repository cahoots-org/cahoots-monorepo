from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from schemas.teams import RoleConfig, ServiceRole, TeamConfig
from services.team_service import TeamService

from cahoots_core.models.service import ServiceTier

router = APIRouter(prefix="/team", tags=["team"])


@router.get("/config")
async def get_team_configuration(team_service: TeamService = Depends()) -> TeamConfig:
    """Get the current team configuration."""
    return await team_service.get_team_config()


@router.put("/config")
async def update_team_configuration(
    config: TeamConfig, team_service: TeamService = Depends()
) -> TeamConfig:
    """Update the entire team configuration."""
    return await team_service.update_team_config(config)


@router.put("/roles/{role}")
async def SeRoleConfigconfiguration(
    role: ServiceRole, config: RoleConfig, team_service: TeamService = Depends()
) -> TeamConfig:
    """Update configuration for a specific role."""
    return await team_service.update_role_config(role, config)


@router.get("/roles")
async def list_available_roles() -> List[Dict]:
    """List available roles and their capabilities."""
    return [
        {
            "role": ServiceRole.DEVELOPER,
            "description": "Implements features, reviews code, and maintains technical documentation",
            "capabilities": [
                "Code generation",
                "Code review",
                "Documentation",
                "Dependency management",
            ],
        },
        {
            "role": ServiceRole.QA_TESTER,
            "description": "Ensures code quality through testing and validation",
            "capabilities": [
                "Test generation",
                "Test execution",
                "Performance testing",
                "Security scanning",
            ],
        },
        {
            "role": ServiceRole.UX_DESIGNER,
            "description": "Handles UI/UX design and implementation",
            "capabilities": [
                "Layout design",
                "Component generation",
                "Accessibility validation",
                "Design system compliance",
            ],
        },
        {
            "role": ServiceRole.PROJECT_MANAGER,
            "description": "Coordinates development activities and tracks progress",
            "capabilities": [
                "Task breakdown",
                "Resource allocation",
                "Progress tracking",
                "Risk assessment",
            ],
        },
    ]


@router.get("/examples")
async def get_configuration_examples() -> Dict[str, TeamConfig]:
    """Get example team configurations for different scenarios."""
    return {
        "solo_developer": TeamConfig(
            project_id="example",
            roles={
                ServiceRole.DEVELOPER: RoleConfig(
                    instances=1,
                    tier=ServiceTier.STANDARD,
                    context_retention_hours=48,
                    max_concurrent_tasks=3,
                    capabilities={"code_review": True, "documentation": True},
                )
            },
            context_limit_mb=50,
            event_retention_days=7,
        ),
        "small_team": TeamConfig(
            project_id="example",
            roles={
                ServiceRole.DEVELOPER: RoleConfig(
                    instances=2,
                    tier=ServiceTier.STANDARD,
                    context_retention_hours=72,
                    max_concurrent_tasks=5,
                    capabilities={"code_review": True, "documentation": True},
                ),
                ServiceRole.QA_TESTER: RoleConfig(
                    instances=1,
                    tier=ServiceTier.STANDARD,
                    context_retention_hours=48,
                    max_concurrent_tasks=3,
                    capabilities={"security_scanning": True, "performance_testing": True},
                ),
            },
            context_limit_mb=100,
            context_sharing_enabled=True,
            event_retention_days=14,
        ),
        "full_team": TeamConfig(
            project_id="example",
            roles={
                ServiceRole.PROJECT_MANAGER: RoleConfig(
                    instances=1,
                    tier=ServiceTier.PREMIUM,
                    context_retention_hours=168,
                    max_concurrent_tasks=10,
                    capabilities={"risk_assessment": True, "resource_planning": True},
                ),
                ServiceRole.DEVELOPER: RoleConfig(
                    instances=3,
                    tier=ServiceTier.PREMIUM,
                    context_retention_hours=96,
                    max_concurrent_tasks=8,
                    capabilities={
                        "code_review": True,
                        "documentation": True,
                        "architecture_design": True,
                    },
                ),
                ServiceRole.UX_DESIGNER: RoleConfig(
                    instances=1,
                    tier=ServiceTier.PREMIUM,
                    context_retention_hours=72,
                    max_concurrent_tasks=5,
                    capabilities={"accessibility_testing": True, "design_system": True},
                ),
                ServiceRole.QA_TESTER: RoleConfig(
                    instances=2,
                    tier=ServiceTier.PREMIUM,
                    context_retention_hours=72,
                    max_concurrent_tasks=6,
                    capabilities={
                        "security_scanning": True,
                        "performance_testing": True,
                        "integration_testing": True,
                    },
                ),
            },
            context_limit_mb=200,
            context_sharing_enabled=True,
            event_retention_days=30,
        ),
        "enterprise_team": TeamConfig(
            project_id="example",
            roles={
                ServiceRole.PROJECT_MANAGER: RoleConfig(
                    instances=2,
                    tier=ServiceTier.ENTERPRISE,
                    context_retention_hours=168,
                    max_concurrent_tasks=15,
                    capabilities={
                        "risk_assessment": True,
                        "resource_planning": True,
                        "portfolio_management": True,
                    },
                ),
                ServiceRole.DEVELOPER: RoleConfig(
                    instances=5,
                    tier=ServiceTier.ENTERPRISE,
                    context_retention_hours=168,
                    max_concurrent_tasks=10,
                    capabilities={
                        "code_review": True,
                        "documentation": True,
                        "architecture_design": True,
                        "performance_optimization": True,
                    },
                ),
                ServiceRole.UX_DESIGNER: RoleConfig(
                    instances=2,
                    tier=ServiceTier.ENTERPRISE,
                    context_retention_hours=96,
                    max_concurrent_tasks=8,
                    capabilities={
                        "accessibility_testing": True,
                        "design_system": True,
                        "user_research": True,
                    },
                ),
                ServiceRole.QA_TESTER: RoleConfig(
                    instances=3,
                    tier=ServiceTier.ENTERPRISE,
                    context_retention_hours=96,
                    max_concurrent_tasks=10,
                    capabilities={
                        "security_scanning": True,
                        "performance_testing": True,
                        "integration_testing": True,
                        "compliance_testing": True,
                    },
                ),
            },
            context_limit_mb=500,
            context_sharing_enabled=True,
            event_retention_days=90,
        ),
    }
