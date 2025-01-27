"""API key verification utilities."""
from typing import Optional, Dict
from cahoots_core.models.user import User
from cahoots_service.api.dependencies import get_db, get_security_manager
from cahoots_service.schemas.auth import EmailVerificationRequest, ResendVerificationRequest
from cahoots_service.services.email_service import EmailService
from cahoots_service.utils.security import SecurityManager
from fastapi import Depends, HTTPException, status, Request, APIRouter
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> str:
    """Verify API key.
    
    Args:
        request: FastAPI request object
        api_key: API key from request header
        security_manager: Security manager instance
        
    Returns:
        str: Organization ID associated with the API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    # Skip verification for health check
    if request.url.path == "/health":
        return "test-org"
        
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key required"
        )
    
    # Authenticate API key
    key_data = await security_manager.authenticate(api_key)
    return key_data["organization_id"]

async def get_current_user(
    api_key: str = Depends(api_key_header),
    security_manager: SecurityManager = Depends(get_security_manager),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from API key.
    
    Args:
        api_key: API key from request header
        security_manager: Security manager instance
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If API key is invalid or user not found
    """
    key_data = await security_manager.authenticate(api_key)
    
    # Look up user
    stmt = select(User).where(User.id == key_data["user_id"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    request: EmailVerificationRequest,
    security_manager: SecurityManager = Depends(get_security_manager),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends()
) -> Dict[str, str]:
    """Verify user email with verification token.
    
    Args:
        request: Email verification request
        security_manager: Security manager instance
        db: Database session
        email_service: Email service
        
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If verification fails
    """
    try:
        # Verify token and get user ID
        user_id = await security_manager.verify_email(request.token)
        
        # Look up user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
            
        # Update user
        user.is_verified = True
        await db.commit()
        
        # Send welcome email
        await email_service.send_welcome_email(
            email=user.email,
            name=user.full_name
        )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    request: ResendVerificationRequest,
    security_manager: SecurityManager = Depends(get_security_manager),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends()
) -> None:
    """Resend verification email.
    
    Args:
        request: Resend verification request
        security_manager: Security manager instance
        db: Database session
        email_service: Email service
        
    Raises:
        HTTPException: If resend fails
    """
    try:
        # Look up user
        stmt = select(User).where(User.id == request.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Create new verification token
        token = await security_manager.create_verification_token(user.id)
        
        # Send verification email
        await email_service.send_verification_email(
            email=user.email,
            token=token
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 