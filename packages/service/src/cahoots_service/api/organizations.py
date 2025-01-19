"""Organization API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from src.core.dependencies import BaseDeps
from src.services.organization_service import OrganizationService
from src.schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)

router = APIRouter(tags=["organizations"])

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    deps: BaseDeps = Depends()
) -> OrganizationResponse:
    """Create a new organization.
    
    Args:
        data: Organization data
        deps: Base dependencies
        
    Returns:
        Created organization
        
    Raises:
        HTTPException: If organization creation fails
    """
    try:
        service = OrganizationService(deps)
        organization = await service.create_organization(data)
        return organization
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    deps: BaseDeps = Depends()
) -> List[OrganizationResponse]:
    """List all organizations.
    
    Args:
        deps: Base dependencies
        
    Returns:
        List of organizations
        
    Raises:
        HTTPException: If organization listing fails
    """
    try:
        service = OrganizationService(deps)
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
    deps: BaseDeps = Depends()
) -> OrganizationResponse:
    """Get organization by ID.
    
    Args:
        organization_id: Organization ID
        deps: Base dependencies
        
    Returns:
        Organization details
        
    Raises:
        HTTPException: If organization not found
    """
    try:
        service = OrganizationService(deps)
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
    deps: BaseDeps = Depends()
) -> OrganizationResponse:
    """Update organization.
    
    Args:
        organization_id: Organization ID
        data: Update data
        deps: Base dependencies
        
    Returns:
        Updated organization
        
    Raises:
        HTTPException: If organization not found or update fails
    """
    try:
        service = OrganizationService(deps)
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
    deps: BaseDeps = Depends()
) -> None:
    """Delete organization.
    
    Args:
        organization_id: Organization ID
        deps: Base dependencies
        
    Raises:
        HTTPException: If organization not found or deletion fails
    """
    try:
        service = OrganizationService(deps)
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