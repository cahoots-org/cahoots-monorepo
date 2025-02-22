"""Organization member management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from cahoots_service.api.dependencies import get_db, get_current_user
from cahoots_service.schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from cahoots_service.schemas.organizations import (
    MemberInvite,
    MemberUpdate,
    MemberResponse
)
from cahoots_service.services.organization_service import OrganizationService
from cahoots_core.models.user import User
from cahoots_core.utils.metrics import MetricsCollector

router = APIRouter(prefix="/{organization_id}/members", tags=["organization-members"])

# Initialize metrics
metrics = MetricsCollector("organization_members")

@router.post("", response_model=APIResponse[MemberResponse])
async def invite_member(
    organization_id: UUID,
    invite: MemberInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[MemberResponse]:
    """Invite a new member to the organization."""
    with metrics.timer("invite_member_duration"):
        try:
            service = OrganizationService(db)
            await service.invite_member(organization_id, invite, current_user.id)
            
            metrics.counter("member_invited_total").inc()
            return APIResponse(
                success=True,
                data=MemberResponse(
                    email=invite.email,
                    role=invite.role,
                    status="invited"
                )
            )
        except Exception as e:
            metrics.counter("member_invite_errors_total").inc()
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="MEMBER_INVITE_ERROR",
                    message=str(e),
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            )

@router.get("", response_model=APIResponse[List[MemberResponse]])
async def list_members(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[MemberResponse]]:
    """List all members in the organization."""
    with metrics.timer("list_members_duration"):
        try:
            service = OrganizationService(db)
            members = await service.list_members(organization_id)
            
            metrics.counter("members_listed_total").inc()
            metrics.gauge("members_count", len(members))
            return APIResponse(
                success=True,
                data=members
            )
        except Exception as e:
            metrics.counter("member_list_errors_total").inc()
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
    organization_id: UUID,
    member_id: UUID,
    update: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[MemberResponse]:
    """Update a member's role or permissions."""
    with metrics.timer("update_member_duration"):
        try:
            service = OrganizationService(db)
            result = await service.update_member(
                organization_id,
                member_id,
                update,
                current_user.id
            )
            
            metrics.counter("member_updated_total").inc()
            return APIResponse(
                success=True,
                data=result
            )
        except Exception as e:
            metrics.counter("member_update_errors_total").inc()
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
    organization_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Remove a member from the organization."""
    with metrics.timer("remove_member_duration"):
        try:
            service = OrganizationService(db)
            await service.remove_member(organization_id, member_id, current_user.id)
            
            metrics.counter("member_removed_total").inc()
            return APIResponse(
                success=True,
                data=True
            )
        except Exception as e:
            metrics.counter("member_remove_errors_total").inc()
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="MEMBER_REMOVE_ERROR",
                    message=str(e),
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            ) 