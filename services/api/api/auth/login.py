"""Login endpoint implementation."""

from api.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Login with email and password.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If login fails
    """
    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.authenticate_user(
            email=request.email, password=request.password
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_service.settings.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
