"""Organization API endpoints."""
from typing import List
from uuid import UUID
from cahoots_core.models.user import User
from cahoots_service.api.auth import get_current_user
from cahoots_service.api.dependencies import get_db
from cahoots_service.schemas.organizations import MemberInvite, MemberResponse, MemberUpdate, OrganizationCreate, OrganizationResponse, OrganizationUpdate, OrganizationWithMembers
from cahoots_service.services.organization_service import OrganizationService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Create a new organization.
    
    Args:
        data: Organization data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created organization
    """
    service = OrganizationService(db)
    return await service.create_organization(data, current_user.id)

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[OrganizationResponse]:
    """List organizations.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of organizations
    """
    service = OrganizationService(db)
    return await service.list_organizations(current_user.id)

@router.get("/{organization_id}", response_model=OrganizationWithMembers)
async def get_organization(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrganizationWithMembers:
    """Get organization by ID.
    
    Args:
        organization_id: Organization ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Organization details with members
        
    Raises:
        HTTPException: If organization not found
    """
    service = OrganizationService(db)
    organization = await service.get_organization(organization_id, include_members=True)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
        
    return organization

@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Update organization.
    
    Args:
        organization_id: Organization ID
        data: Update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated organization
        
    Raises:
        HTTPException: If organization not found
    """
    service = OrganizationService(db)
    organization = await service.update_organization(
        organization_id,
        data,
        current_user.id
    )
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
        
    return organization

@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete organization.
    
    Args:
        organization_id: Organization ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If organization not found
    """
    service = OrganizationService(db)
    deleted = await service.delete_organization(organization_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

@router.post("/{organization_id}/members/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_member(
    organization_id: UUID,
    invite: MemberInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Invite user to organization.
    
    Args:
        organization_id: Organization ID
        invite: Member invitation
        current_user: Current authenticated user
        db: Database session
    """
    service = OrganizationService(db)
    await service.invite_member(organization_id, invite, current_user.id)

@router.get("/{organization_id}/members", response_model=List[MemberResponse])
async def list_members(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[MemberResponse]:
    """List organization members.
    
    Args:
        organization_id: Organization ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of members
    """
    service = OrganizationService(db)
    return await service.list_members(organization_id)

@router.patch("/{organization_id}/members/{user_id}", response_model=MemberResponse)
async def update_member(
    organization_id: UUID,
    user_id: UUID,
    update: MemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MemberResponse:
    """Update organization member.
    
    Args:
        organization_id: Organization ID
        user_id: User ID to update
        update: Member update
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated member details
    """
    service = OrganizationService(db)
    return await service.update_member(organization_id, user_id, update, current_user.id)

@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove member from organization.
    
    Args:
        organization_id: Organization ID
        user_id: User ID to remove
        current_user: Current authenticated user
        db: Database session
    """
    service = OrganizationService(db)
    await service.remove_member(organization_id, user_id, current_user.id) 