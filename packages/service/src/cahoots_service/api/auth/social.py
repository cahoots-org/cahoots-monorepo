"""Social authentication endpoints."""
from cahoots_service.api.dependencies import get_db
from cahoots_service.schemas.auth import SocialAuthRequest, TokenResponse
from cahoots_service.services.auth_service import AuthService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/social/{provider}", response_model=TokenResponse)
async def social_auth(
    provider: str,
    request: SocialAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticate with social provider.
    
    Args:
        provider: Social provider (google, github)
        request: Social auth credentials
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If social auth fails
    """
    auth_service = AuthService(db)
    
    if provider not in ["google", "github"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}"
        )
    
    try:
        user, access_token, refresh_token = await auth_service.authenticate_social(
            provider=provider,
            token=request.token,
            provider_user_id=request.provider_user_id,
            provider_data=request.provider_data
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_service.settings.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 