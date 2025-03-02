"""Authentication endpoints."""

from typing import Any, Dict

from api.dependencies import get_db, get_security_manager
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.auth import (
    EmailVerificationRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from schemas.base import APIResponse
from services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import SecurityManager

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    security_manager: SecurityManager = Depends(get_security_manager),
) -> APIResponse[TokenResponse]:
    """Login with email and password."""
    auth_service = AuthService(db, security_manager)
    await auth_service.initialize()

    try:
        user, access_token, refresh_token = await auth_service.authenticate_user(
            email=request.email, password=request.password
        )

        return APIResponse(
            success=True,
            data=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=security_manager.config.access_token_expire_minutes * 60,
            ),
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error={
                "code": "AUTH_ERROR",
                "message": str(e),
                "category": "authentication",
                "severity": "error",
            },
        )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    security_manager: SecurityManager = Depends(get_security_manager),
) -> APIResponse[TokenResponse]:
    """Refresh access token."""
    auth_service = AuthService(db, security_manager)
    await auth_service.initialize()

    try:
        access_token, refresh_token = await auth_service.refresh_tokens(request.refresh_token)

        return APIResponse(
            success=True,
            data=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=security_manager.config.access_token_expire_minutes * 60,
            ),
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error={
                "code": "REFRESH_ERROR",
                "message": str(e),
                "category": "authentication",
                "severity": "error",
            },
        )


@router.post("/verify", response_model=APIResponse[Dict[str, Any]])
async def verify_token(
    db: AsyncSession = Depends(get_db),
    security_manager: SecurityManager = Depends(get_security_manager),
) -> APIResponse[Dict[str, Any]]:
    """Verify current token."""
    try:
        user = await security_manager.get_current_user()
        return APIResponse(
            success=True,
            data={"user_id": str(user.id), "email": user.email, "is_verified": user.is_verified},
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error={
                "code": "VERIFY_ERROR",
                "message": str(e),
                "category": "authentication",
                "severity": "error",
            },
        )


# Include other auth endpoints (password reset, email verification, etc.)
from .social import router as social_router

router.include_router(social_router)
