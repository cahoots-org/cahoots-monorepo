"""Password management endpoints."""
from typing import Dict
from cahoots_core.models.user import User
from api.auth import get_current_user
from api.dependencies import get_db
from schemas.auth import PasswordChangeRequest
from services.auth_service import AuthService
from services.email_service import EmailService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["auth"])

class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr

class PasswordReset(BaseModel):
    """Password reset model."""
    token: str
    new_password: str

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Change user password.
    
    Args:
        request: Password change request
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If password change fails
    """
    auth_service = AuthService(db)
    
    try:
        await auth_service.change_password(
            user=current_user,
            current_password=request.current_password,
            new_password=request.new_password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Request password reset.
    
    Args:
        request: Password reset request
        db: Database session
        
    Raises:
        HTTPException: If password reset request fails
    """
    auth_service = AuthService(db)
    email_service = EmailService()
    
    try:
        user, reset_token = await auth_service.create_password_reset(
            email=request.email
        )
        
        await email_service.send_password_reset_email(
            email=user.email,
            token=reset_token
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    request: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Reset password using reset token.
    
    Args:
        request: Password reset
        db: Database session
        
    Raises:
        HTTPException: If password reset fails
    """
    auth_service = AuthService(db)
    
    try:
        await auth_service.reset_password(
            token=request.token,
            new_password=request.new_password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 