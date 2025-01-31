"""User registration functionality."""
from typing import Dict
from cahoots_core.models.user import User
from cahoots_service.api.dependencies import get_db, get_security_manager
from cahoots_service.services.email_service import EmailService
from cahoots_service.utils.security import SecurityManager
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegistration(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: str
    full_name: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    registration: UserRegistration,
    security_manager: SecurityManager = Depends(get_security_manager),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends()
) -> Dict[str, str]:
    """Register a new user.
    
    Args:
        registration: User registration data
        security_manager: Security manager for password hashing
        db: Database session
        email_service: Email service for verification
        
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If registration fails
    """
    # Check if email exists
    user = await security_manager.get_user_by_email(registration.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = await security_manager.hash_password(registration.password)
    verification_token = await security_manager.generate_verification_token()
    
    new_user = User(
        email=registration.email,
        full_name=registration.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=False,
        verification_token=verification_token
    )
    
    try:
        # Save user
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Send verification email
        await email_service.send_verification_email(
            email=registration.email,
            token=verification_token
        )
        
        return {
            "message": "Registration successful. Please check your email to verify your account."
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 