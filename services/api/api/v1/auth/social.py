"""Social authentication endpoints."""

import logging
from typing import Any, Dict

from api.dependencies import get_db, get_security_manager
from fastapi import APIRouter, Depends, HTTPException, Request, status
from schemas.auth import GoogleUserData, SocialLoginRequest, TokenResponse
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from utils.config import get_settings
from utils.security import SecurityManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social", tags=["auth"])


@router.post("/{provider}", response_model=APIResponse)
async def social_auth(
    provider: str,
    request: SocialLoginRequest,
    db: AsyncSession = Depends(get_db),
    security: SecurityManager = Depends(get_security_manager),
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider mismatch")

        auth_service = AuthService(db, security)
        user, access_token, refresh_token = await auth_service.authenticate_social(
            provider=provider, user_data=request.user_data
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
                    "role": user.role,
                },
            },
        )
    except HTTPException as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_ERROR",
                message=str(e.detail),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.ERROR,
            ),
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_ERROR",
                message=str(e),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/callback/{provider}")
async def oauth_callback(provider: str) -> APIResponse[Dict[str, Any]]:
    """Handle OAuth callback."""
    return APIResponse(success=True, data={})  # Frontend handles the OAuth flow
