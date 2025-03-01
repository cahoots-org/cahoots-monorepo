"""Organization team management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.organizations import (
    TeamAssignment,
    TeamResponse
)
from services.organization_service import OrganizationService
from cahoots_core.models.user import User
from cahoots_core.utils.metrics import MetricsCollector

router = APIRouter(prefix="/{organization_id}/teams", tags=["organization-teams"])

# Initialize metrics
metrics = MetricsCollector("organization_teams")

@router.post("", response_model=APIResponse[TeamResponse])
async def assign_team(
    organization_id: UUID,
    assignment: TeamAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[TeamResponse]:
    """Assign a team to the organization."""
    with metrics.timer("assign_team_duration"):
        try:
            service = OrganizationService(db)
            result = await service.assign_team(
                organization_id,
                assignment.team_id,
                current_user.id
            )
            
            metrics.counter("team_assigned_total").inc()
            return APIResponse(
                success=True,
                data=result
            )
        except Exception as e:
            metrics.counter("team_assign_errors_total").inc()
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
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[TeamResponse]]:
    """List all teams in the organization."""
    with metrics.timer("list_teams_duration"):
        try:
            service = OrganizationService(db)
            teams = await service.list_organization_teams(organization_id)
            
            metrics.counter("teams_listed_total").inc()
            metrics.gauge("teams_count", len(teams))
            return APIResponse(
                success=True,
                data=teams
            )
        except Exception as e:
            metrics.counter("team_list_errors_total").inc()
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
    organization_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Remove a team from the organization."""
    with metrics.timer("remove_team_duration"):
        try:
            service = OrganizationService(db)
            result = await service.remove_team(
                organization_id,
                team_id,
                current_user.id
            )
            
            metrics.counter("team_removed_total").inc()
            return APIResponse(
                success=True,
                data=result
            )
        except Exception as e:
            metrics.counter("team_remove_errors_total").inc()
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="TEAM_REMOVE_ERROR",
                    message=str(e),
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            ) 