"""Team role management endpoints."""

from typing import Any, Dict, List
from uuid import UUID

from api.dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from schemas.teams import RoleCreate, RoleResponse, RoleUpdate
from services.team_service import TeamService
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.models.user import User

router = APIRouter(prefix="/{team_id}/roles", tags=["team-roles"])


@router.post("", response_model=APIResponse[RoleResponse])
async def create_role(
    team_id: UUID,
    role: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[RoleResponse]:
    """Create a new team role."""
    try:
        service = TeamService(db)
        result = await service.create_role(team_id, role, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ROLE_CREATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("", response_model=APIResponse[List[RoleResponse]])
async def list_roles(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[RoleResponse]]:
    """List all roles in a team."""
    try:
        service = TeamService(db)
        roles = await service.list_roles(team_id, current_user.id)

        return APIResponse(success=True, data=roles)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ROLE_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/{role_id}", response_model=APIResponse[RoleResponse])
async def get_role(
    team_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[RoleResponse]:
    """Get a specific role by ID."""
    try:
        service = TeamService(db)
        role = await service.get_role(team_id, role_id, current_user.id)

        return APIResponse(success=True, data=role)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ROLE_GET_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.put("/{role_id}", response_model=APIResponse[RoleResponse])
async def update_role(
    team_id: UUID,
    role_id: UUID,
    role: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[RoleResponse]:
    """Update a team role."""
    try:
        service = TeamService(db)
        result = await service.update_role(team_id, role_id, role, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ROLE_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.delete("/{role_id}", response_model=APIResponse[bool])
async def delete_role(
    team_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """Delete a team role."""
    try:
        service = TeamService(db)
        result = await service.delete_role(team_id, role_id, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ROLE_DELETE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )
