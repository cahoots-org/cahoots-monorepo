"""Token management endpoints."""
from api.dependencies import get_security_manager
from schemas.auth import RefreshTokenRequest, TokenResponse
from utils.security import SecurityManager
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    security_manager: SecurityManager = Depends(get_security_manager)
) -> TokenResponse:
    """Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        security_manager: Security manager instance
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If token refresh fails
    """
    try:
        # Validate refresh token
        payload = await security_manager.validate_token(request.refresh_token)
        
        # Create new tokens
        access_token, refresh_token = await security_manager.create_tokens(payload["sub"])
        
        # Revoke old refresh token
        await security_manager.revoke_token(request.refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=security_manager.config.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshTokenRequest,
    security_manager: SecurityManager = Depends(get_security_manager)
) -> None:
    """Logout by revoking refresh token.
    
    Args:
        request: Refresh token to revoke
        security_manager: Security manager instance
        
    Raises:
        HTTPException: If token revocation fails
    """
    try:
        await security_manager.revoke_token(request.refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 