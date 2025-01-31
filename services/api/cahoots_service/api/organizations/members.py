"""Organization member management endpoints."""
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from cahoots_core.models.user import User, UserRole
from cahoots_core.exceptions import ServiceError

from ...schemas.organizations import MemberInvite, MemberUpdate, MemberResponse
from ...services.organization_service import OrganizationService
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/organizations/{organization_id}/members", tags=["members"])

class MemberInvite(BaseModel):
    """Member invitation request."""
    email: EmailStr
    role: str = "member"

class MemberUpdate(BaseModel):
    """Member update request."""
    role: str

class MemberResponse(BaseModel):
    """Member response model."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    organization_id: UUID,
    invite: MemberInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Invite a new member to the organization.
    
    Args:
        organization_id: Organization ID
        invite: Invitation details
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If invitation fails
    """
    service = OrganizationService(db)
    await service.invite_member(organization_id, invite, current_user.id)
    return {"message": "Invitation sent successfully"}

@router.get("", response_model=List[MemberResponse])
async def list_members(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[MemberResponse]:
    """List organization members.
    
    Args:
        organization_id: Organization ID
        db: Database session
        
    Returns:
        List of members
    """
    stmt = select(User).join(
        UserRole,
        User.organizations.any(UserRole.organization_id == str(organization_id))
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        MemberResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=next(
                role.role for role in user.organizations 
                if role.organization_id == str(organization_id)
            ),
            is_active=user.is_active
        )
        for user in users
    ]

@router.patch("/{user_id}", response_model=MemberResponse)
async def update_member(
    organization_id: UUID,
    user_id: UUID,
    update: MemberUpdate,
    db: AsyncSession = Depends(get_db)
) -> MemberResponse:
    """Update member role.
    
    Args:
        organization_id: Organization ID
        user_id: User ID
        update: Update data
        db: Database session
        
    Returns:
        Updated member details
        
    Raises:
        HTTPException: If update fails
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update role
    for role in user.organizations:
        if role.organization_id == str(organization_id):
            role.role = update.role
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member"
        )
    
    await db.commit()
    
    return MemberResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=update.role,
        is_active=user.is_active
    )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove member from organization.
    
    Args:
        organization_id: Organization ID
        user_id: User ID
        db: Database session
        
    Raises:
        HTTPException: If removal fails
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove from organization
    user.organizations = [
        role for role in user.organizations
        if role.organization_id != str(organization_id)
    ]
    
    await db.commit() 