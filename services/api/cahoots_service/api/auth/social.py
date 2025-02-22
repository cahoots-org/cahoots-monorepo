"""Social authentication endpoints."""
from cahoots_service.api.dependencies import get_db, get_security_config, get_security_manager
from cahoots_service.schemas.auth import TokenResponse, RefreshTokenRequest
from cahoots_service.services.auth_service import AuthService
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import logging
from typing import Dict, Any
from cahoots_core.utils.config import SecurityConfig
from cahoots_service.utils.security import SecurityManager
from cahoots_service.utils.config import get_settings

logger = logging.getLogger(__name__)

class GoogleUserData(BaseModel):
    """Google user data schema."""
    id: str
    email: EmailStr
    name: str
    picture: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    verified_email: bool | None = None

router = APIRouter(prefix="/auth", tags=["auth"])

def validate_oauth_config():
    """Validate OAuth configuration."""
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        logger.error("[OAUTH_FLOW] Missing Google OAuth credentials")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not properly configured"
        )

@router.get("/google/callback")
async def google_callback():
    """Handle Google OAuth callback."""
    return {}  # Just return empty response, the frontend handles the code

@router.post("/social/{provider}", response_model=TokenResponse)
async def social_auth(
    provider: str,
    user_data: GoogleUserData,
    request_obj: Request,
    db: AsyncSession = Depends(get_db),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> TokenResponse:
    """Create or update user from social data and return tokens."""
    # Validate OAuth configuration first
    validate_oauth_config()
    
    logger.info("[OAUTH_FLOW] Received social auth request:", extra={
        "provider": provider,
        "user_id": user_data.id,
        "email": user_data.email,
        "name": user_data.name,
        "request_headers": dict(request_obj.headers),
        "request_method": request_obj.method,
        "request_url": str(request_obj.url)
    })
    
    # Log the full user data for debugging
    logger.info("[OAUTH_FLOW] Full user data:", extra={
        "user_data": user_data.model_dump()
    })
    
    if provider not in ["google", "github"]:
        logger.error(f"[OAUTH_FLOW] Invalid provider: {provider}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}"
        )
    
    try:
        # Initialize auth service with security manager
        auth_service = AuthService(db, security_manager)
        await auth_service.initialize()
        logger.info("[OAUTH_FLOW] Creating/updating user from social data")
        
        # Convert Pydantic model to dict for handle_social_user
        user_dict = user_data.model_dump()
        logger.info("[OAUTH_FLOW] Converted user data:", extra={
            "user_dict": user_dict
        })
        
        # Create/update user and generate tokens
        user, access_token, refresh_token = await auth_service.handle_social_user(
            provider=provider,
            user_data=user_dict
        )
        
        logger.info("[OAUTH_FLOW] Social authentication successful:", extra={
            "user_id": str(user.id),
            "email": user.email,
            "has_access_token": bool(access_token),
            "has_refresh_token": bool(refresh_token)
        })
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=security_manager.config.access_token_expire_minutes * 60
        )
    except Exception as e:
        logger.error("[OAUTH_FLOW] Social authentication failed:", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "provider": provider,
            "traceback": getattr(e, "__traceback__", None)
        })
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Social authentication failed: {str(e)}"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> TokenResponse:
    """Refresh access token."""
    auth_service = AuthService(db, security_manager)
    await auth_service.initialize()
    access_token, refresh_token = await auth_service.refresh_tokens(request.refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=security_manager.config.access_token_expire_minutes * 60
    ) 