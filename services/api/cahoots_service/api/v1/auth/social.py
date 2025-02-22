"""Social authentication endpoints."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from cahoots_service.api.dependencies import get_db, get_security_manager
from cahoots_service.schemas.auth import TokenResponse, GoogleUserData, SocialLoginRequest
from cahoots_service.schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from cahoots_service.services.auth_service import AuthService
from cahoots_service.utils.security import SecurityManager
from cahoots_service.utils.config import get_settings

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social", tags=["auth"])

@router.post("/{provider}", response_model=APIResponse)
async def social_auth(
    provider: str,
    request: SocialLoginRequest,
    db: AsyncSession = Depends(get_db),
    security: SecurityManager = Depends(get_security_manager)
) -> APIResponse:
    """Handle social authentication.
    
    Args:
        provider: Social provider (google/github)
        request: Social login request data
        db: Database session
        security: Security manager instance
        
    Returns:
        API response with tokens
    """
    try:
        # Validate provider matches
        if provider != request.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider mismatch"
            )

        auth_service = AuthService(db, security)
        user, access_token, refresh_token = await auth_service.authenticate_social(
            provider=provider,
            user_data=request.user_data
        )

        return APIResponse(
            success=True,
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.full_name,
                    "role": user.role
                }
            }
        )
    except HTTPException as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_ERROR",
                message=str(e.detail),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.ERROR
            )
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_ERROR",
                message=str(e),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/callback/{provider}")
async def oauth_callback(provider: str) -> APIResponse[Dict[str, Any]]:
    """Handle OAuth callback."""
    return APIResponse(
        success=True,
        data={}  # Frontend handles the OAuth flow
    ) 