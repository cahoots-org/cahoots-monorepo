"""Organization management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationWithMembers
)
from services.organization_service import OrganizationService
from cahoots_core.models.user import User
from cahoots_core.utils.metrics import MetricsCollector

from .members import router as members_router
from .teams import router as teams_router

router = APIRouter(prefix="/organizations", tags=["organizations"])

# Include sub-routers
router.include_router(members_router)
router.include_router(teams_router)

# Initialize metrics
metrics = MetricsCollector("organizations")

@router.post("", response_model=APIResponse[OrganizationResponse])
async def create_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[OrganizationResponse]:
    """Create a new organization."""
    with metrics.timer("create_organization_duration"):
        try:
            service = OrganizationService(db)
            result = await service.create_organization(organization, current_user.id)
            
            metrics.counter("organization_created_total").inc()
            return APIResponse(
                success=True,
                data=result
            )
        except Exception as e:
            metrics.counter("organization_create_errors_total").inc()
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="ORGANIZATION_CREATE_ERROR",
                    message=str(e),
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            )

@router.get("", response_model=APIResponse[List[OrganizationResponse]])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[OrganizationResponse]]:
    """List all organizations with optional search and pagination."""
    try:
        service = OrganizationService(db)
        organizations = await service.list_organizations(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search
        )
        
        return APIResponse(
            success=True,
            data=organizations
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ORGANIZATION_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/{organization_id}", response_model=APIResponse[OrganizationWithMembers])
async def get_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[OrganizationWithMembers]:
    """Get a specific organization by ID."""
    with metrics.timer("get_organization_duration"):
        try:
            service = OrganizationService(db)
            organization = await service.get_organization(
                organization_id,
                include_members=True
            )
            
            if not organization:
                metrics.counter("organization_not_found_total").inc()
                return APIResponse(
                    success=False,
                    error=ErrorDetail(
                        code="ORGANIZATION_NOT_FOUND",
                        message="Organization not found",
                        category=ErrorCategory.BUSINESS_LOGIC,
                        severity=ErrorSeverity.ERROR
                    )
                )
            
            metrics.counter("organization_retrieved_total").inc()
            return APIResponse(
                success=True,
                data=organization
            )
        except Exception as e:
            metrics.counter("organization_get_errors_total").inc()
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="ORGANIZATION_GET_ERROR",
                    message=str(e),
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            )

@router.put("/{organization_id}", response_model=APIResponse[OrganizationResponse])
async def update_organization(
    organization_id: UUID,
    organization: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[OrganizationResponse]:
    """Update a specific organization."""
    try:
        service = OrganizationService(db)
        result = await service.update_organization(
            organization_id,
            organization,
            current_user.id
        )
        
        if not result:
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="ORGANIZATION_NOT_FOUND",
                    message="Organization not found",
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            )
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ORGANIZATION_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.delete("/{organization_id}", response_model=APIResponse[bool])
async def delete_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Delete a specific organization."""
    try:
        service = OrganizationService(db)
        result = await service.delete_organization(organization_id, current_user.id)
        
        if not result:
            return APIResponse(
                success=False,
                error=ErrorDetail(
                    code="ORGANIZATION_NOT_FOUND",
                    message="Organization not found",
                    category=ErrorCategory.BUSINESS_LOGIC,
                    severity=ErrorSeverity.ERROR
                )
            )
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ORGANIZATION_DELETE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 