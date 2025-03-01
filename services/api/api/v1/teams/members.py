"""Team member management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.teams import MemberCreate, MemberUpdate, MemberResponse
from services.team_service import TeamService
from cahoots_core.models.user import User

router = APIRouter(prefix="/{team_id}/members", tags=["team-members"])

@router.post("", response_model=APIResponse[MemberResponse])
async def add_member(
    team_id: UUID,
    member: MemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[MemberResponse]:
    """Add a member to a team."""
    try:
        service = TeamService(db)
        result = await service.add_member(team_id, member, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="MEMBER_ADD_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("", response_model=APIResponse[List[MemberResponse]])
async def list_members(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[MemberResponse]]:
    """List all members in a team."""
    try:
        service = TeamService(db)
        members = await service.list_members(team_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=members
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="MEMBER_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.put("/{member_id}", response_model=APIResponse[MemberResponse])
async def update_member(
    team_id: UUID,
    member_id: UUID,
    member: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[MemberResponse]:
    """Update a team member's role or permissions."""
    try:
        service = TeamService(db)
        result = await service.update_member(team_id, member_id, member, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="MEMBER_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.delete("/{member_id}", response_model=APIResponse[bool])
async def remove_member(
    team_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Remove a member from a team."""
    try:
        service = TeamService(db)
        result = await service.remove_member(team_id, member_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="MEMBER_REMOVE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 