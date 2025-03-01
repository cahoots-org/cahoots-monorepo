"""Project team management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.teams import TeamAssignment, TeamResponse
from services.team_service import TeamService
from cahoots_core.models.user import User

router = APIRouter(prefix="/{project_id}/teams", tags=["project-teams"])

@router.post("", response_model=APIResponse[TeamResponse])
async def assign_team(
    project_id: UUID,
    assignment: TeamAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[TeamResponse]:
    """Assign a team to a project."""
    try:
        service = TeamService(db)
        result = await service.assign_team(project_id, assignment.team_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_ASSIGN_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("", response_model=APIResponse[List[TeamResponse]])
async def list_teams(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[TeamResponse]]:
    """List teams assigned to a project."""
    try:
        service = TeamService(db)
        teams = await service.list_project_teams(project_id)
        
        return APIResponse(
            success=True,
            data=teams
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.delete("/{team_id}", response_model=APIResponse[bool])
async def remove_team(
    project_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Remove a team from a project."""
    try:
        service = TeamService(db)
        result = await service.remove_team(project_id, team_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_REMOVE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 