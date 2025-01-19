"""Team management routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.models.team_config import TeamConfig, ServiceRole, RoleConfig
from src.services.team_service import TeamService
from src.core.dependencies import ServiceDeps

router = APIRouter(prefix="/teams", tags=["teams"])

async def get_team_service(
    project_id: str,
    deps: ServiceDeps = Depends()
) -> TeamService:
    """Get team service instance."""
    return TeamService(deps, project_id)

@router.get("/{project_id}/config")
async def get_team_config(
    service: TeamService = Depends(get_team_service)
) -> TeamConfig:
    """Get team configuration."""
    return await service.get_team_config()

@router.put("/{project_id}/config")
async def update_team_config(
    config: TeamConfig,
    service: TeamService = Depends(get_team_service)
) -> TeamConfig:
    """Update team configuration."""
    return await service.update_team_config(config)

@router.put("/{project_id}/roles/{role}")
async def update_role_config(
    role: ServiceRole,
    config: RoleConfig,
    service: TeamService = Depends(get_team_service)
) -> TeamConfig:
    """Update role configuration."""
    return await service.update_role_config(role, config) 