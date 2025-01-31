"""Team management routes."""
from typing import Dict, Any
from cahoots_service.api.dependencies import get_db, ServiceDeps
from cahoots_service.schemas.teams import (
    ServiceRole,
    RoleConfig,
    TeamConfig,
    TeamConfigResponse
)
from cahoots_service.services.team_service import TeamService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/teams", tags=["teams"])

async def get_team_service(
    project_id: str,
    deps: ServiceDeps = Depends(),
    db: Session = Depends(get_db)
) -> TeamService:
    """
    Get team service instance.
    
    Args:
        project_id: The project identifier
        deps: Service dependencies
        db: Database session
        
    Returns:
        TeamService instance
    """
    try:
        return TeamService(deps=deps, db=db, project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/config", response_model=TeamConfigResponse)
async def get_team_config(
    project_id: str,
    service: TeamService = Depends(get_team_service)
) -> TeamConfigResponse:
    """
    Get team configuration.
    
    Args:
        project_id: The project identifier
        service: Team service instance
        
    Returns:
        Current team configuration
    """
    try:
        config = await service.get_team_config()
        return TeamConfigResponse(project_id=project_id, config=config)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{project_id}/config", response_model=TeamConfigResponse)
async def update_team_config(
    project_id: str,
    config: TeamConfig,
    service: TeamService = Depends(get_team_service)
) -> TeamConfigResponse:
    """
    Update team configuration.
    
    Args:
        project_id: The project identifier
        config: New team configuration
        service: Team service instance
        
    Returns:
        Updated team configuration
    """
    try:
        updated_config = await service.update_team_config(config)
        return TeamConfigResponse(project_id=project_id, config=updated_config)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{project_id}/roles/{role}", response_model=TeamConfigResponse)
async def update_role_config(
    project_id: str,
    role: ServiceRole,
    config: RoleConfig,
    service: TeamService = Depends(get_team_service)
) -> TeamConfigResponse:
    """
    Update role configuration.
    
    Args:
        project_id: The project identifier
        role: Service role to update
        config: New role configuration
        service: Team service instance
        
    Returns:
        Updated team configuration
    """
    try:
        updated_config = await service.update_role_config(role, config)
        return TeamConfigResponse(project_id=project_id, config=updated_config)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 