"""Team management endpoints."""

from typing import List, Optional
from uuid import UUID

from api.dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from schemas.teams import TeamCreate, TeamResponse, TeamUpdate
from services.team_service import TeamService
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.models.user import User

from .members import router as members_router
from .roles import router as roles_router

router = APIRouter(prefix="/teams", tags=["teams"])

# Include sub-routers
router.include_router(members_router)
router.include_router(roles_router)


@router.post("", response_model=APIResponse[TeamResponse])
async def create_team(
    team: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TeamResponse]:
    """Create a new team."""
    try:
        service = TeamService(db)
        result = await service.create_team(team, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_CREATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("", response_model=APIResponse[List[TeamResponse]])
async def list_teams(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[TeamResponse]]:
    """List all teams with optional search and pagination."""
    try:
        service = TeamService(db)
        teams = await service.list_teams(skip, limit, search, current_user.id)

        return APIResponse(success=True, data=teams)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/{team_id}", response_model=APIResponse[TeamResponse])
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TeamResponse]:
    """Get a specific team by ID."""
    try:
        service = TeamService(db)
        team = await service.get_team(team_id, current_user.id)

        return APIResponse(success=True, data=team)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_GET_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.put("/{team_id}", response_model=APIResponse[TeamResponse])
async def update_team(
    team_id: UUID,
    team: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TeamResponse]:
    """Update a specific team."""
    try:
        service = TeamService(db)
        result = await service.update_team(team_id, team, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.delete("/{team_id}", response_model=APIResponse[bool])
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """Delete a specific team."""
    try:
        service = TeamService(db)
        result = await service.delete_team(team_id, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="TEAM_DELETE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )
