"""Organization API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_session
from src.services.organization_service import OrganizationService
from src.schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_session)
) -> OrganizationResponse:
    """Create a new organization.
    
    Args:
        data: Organization data
        db: Database session
        
    Returns:
        Created organization
        
    Raises:
        HTTPException: If organization creation fails
    """
    try:
        service = OrganizationService(db)
        organization = await service.create_organization(data)
        return organization
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_session)
) -> List[OrganizationResponse]:
    """List all organizations.
    
    Args:
        db: Database session
        
    Returns:
        List of organizations
        
    Raises:
        HTTPException: If organization listing fails
    """
    try:
        service = OrganizationService(db)
        organizations = await service.list_organizations()
        return organizations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_session)
) -> OrganizationResponse:
    """Get organization by ID.
    
    Args:
        organization_id: Organization ID
        db: Database session
        
    Returns:
        Organization details
        
    Raises:
        HTTPException: If organization not found
    """
    try:
        service = OrganizationService(db)
        organization = await service.get_organization(organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return organization
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_session)
) -> OrganizationResponse:
    """Update organization.
    
    Args:
        organization_id: Organization ID
        data: Update data
        db: Database session
        
    Returns:
        Updated organization
        
    Raises:
        HTTPException: If organization not found or update fails
    """
    try:
        service = OrganizationService(db)
        organization = await service.update_organization(organization_id, data)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return organization
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_session)
) -> None:
    """Delete organization.
    
    Args:
        organization_id: Organization ID
        db: Database session
        
    Raises:
        HTTPException: If organization not found or deletion fails
    """
    try:
        service = OrganizationService(db)
        deleted = await service.delete_organization(organization_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 