"""Organization invitation endpoints."""
from typing import Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from cahoots_core.models.invitation import OrganizationInvitation
from cahoots_core.models.user import User, UserRole

from ...services.organization_service import OrganizationService
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/organizations/{organization_id}/invitations", tags=["invitations"])

@router.post("/accept-invite/{token}", status_code=status.HTTP_200_OK)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Accept an organization invitation.
    
    Args:
        token: Invitation token
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If acceptance fails
    """
    # Find invitation
    stmt = select(OrganizationInvitation).where(
        OrganizationInvitation.token == token,
        OrganizationInvitation.is_accepted == False,
        OrganizationInvitation.expires_at > datetime.utcnow()
    )
    result = await db.execute(stmt)
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation"
        )
    
    # Verify email matches
    if invitation.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation is for a different email address"
        )
    
    # Check if already a member
    if any(role.organization_id == str(invitation.organization_id) for role in current_user.organizations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this organization"
        )
    
    try:
        # Add user to organization
        role = UserRole(
            user_id=current_user.id,
            organization_id=invitation.organization_id,
            role=invitation.role
        )
        db.add(role)
        
        # Mark invitation as accepted
        invitation.is_accepted = True
        invitation.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Get organization name for response
        org_service = OrganizationService(db)
        organization = await org_service.get_organization(invitation.organization_id)
        
        return {
            "message": f"Successfully joined {organization.name} as {invitation.role}"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 