"""OAuth authentication routes."""

import os
import json
import uuid
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import httpx
import jwt

from app.api.dependencies import get_redis_client

router = APIRouter(prefix="/api/auth", tags=["auth"])

# OAuth configuration - read lazily to ensure Fly secrets are available
def get_google_client_id():
    return os.environ.get("GOOGLE_CLIENT_ID")

def get_google_client_secret():
    return os.environ.get("GOOGLE_CLIENT_SECRET")

def get_jwt_secret_key():
    return os.environ.get("JWT_SECRET_KEY", "dev-secret-key")

def get_environment():
    return os.environ.get("ENVIRONMENT", "development")

def get_redirect_uri():
    if get_environment() == "production":
        return "https://cahoots-frontend.fly.dev/oauth/google/callback"
    return "http://localhost:3000/oauth/google/callback"

def get_frontend_url():
    if get_environment() == "production":
        return "https://cahoots-frontend.fly.dev"
    return "http://localhost:3000"


class OAuthState(BaseModel):
    state: str
    redirect_uri: str


class ExchangeAuthCodeRequest(BaseModel):
    code: str


@router.get("/google/authorize", response_model=OAuthState)
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    client_id = get_google_client_id()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )

    # Generate state token
    state = jwt.encode(
        {
            "provider": "google",
            "redirect_uri": get_redirect_uri(),
            "exp": datetime.utcnow() + timedelta(minutes=10),
            "nonce": str(uuid.uuid4())
        },
        get_jwt_secret_key(),
        algorithm="HS256"
    )

    # Build Google OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }

    auth_url = "https://accounts.google.com/o/oauth2/auth?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )

    return OAuthState(state=state, redirect_uri=auth_url)


@router.post("/google/exchange")
async def exchange_auth_code(
    request: ExchangeAuthCodeRequest,
    redis_client = Depends(get_redis_client)
):
    """Exchange Google authorization code for access token and user info."""
    client_id = get_google_client_id()
    client_secret = get_google_client_secret()

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )

    try:
        # Exchange code for token
        async with httpx.AsyncClient() as http_client:
            token_response = await http_client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": request.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": get_redirect_uri(),
                    "grant_type": "authorization_code"
                }
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info
            user_response = await http_client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information"
                )

            user_info = user_response.json()

            # Create user session in Redis
            user_id = f"google_{user_info['sub']}"
            user_data = {
                "id": user_id,
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "provider": "google",
                "created_at": datetime.utcnow().isoformat()
            }

            # Store user in Redis
            await redis_client.setex(
                f"user:{user_id}",
                86400,  # 24 hours
                json.dumps(user_data)
            )

            # Generate JWT token
            jwt_token = jwt.encode(
                {
                    "sub": user_id,
                    "email": user_info.get("email"),
                    "exp": datetime.utcnow() + timedelta(days=7)
                },
                get_jwt_secret_key(),
                algorithm="HS256"
            )

            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": user_data
            }

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth error: {str(e)}"
        )


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    redis_client = Depends(get_redis_client)
):
    """Handle Google OAuth callback."""
    # This is typically handled by the frontend, but we include it for completeness
    # The frontend should call /auth/google/exchange with the code
    return RedirectResponse(
        url=f"{get_frontend_url()}/oauth/google/callback?code={code}&state={state}"
    )


@router.get("/me")
async def get_current_user(
    request: Request,
    redis_client = Depends(get_redis_client)
):
    """Get current user from JWT token."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=["HS256"])
        user_id = payload.get("sub")

        # Get user from Redis
        user_data = await redis_client.get(f"user:{user_id}")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return json.loads(user_data)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    redis_client = Depends(get_redis_client)
):
    """Refresh an expired JWT token."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )

    old_token = authorization.replace("Bearer ", "")

    # Check for development bypass token
    if old_token == "dev-bypass-token" and get_environment() == "development":
        return {
            "access_token": "dev-bypass-token",
            "token_type": "bearer"
        }

    try:
        # Decode without verifying expiration to get user info
        payload = jwt.decode(
            old_token,
            get_jwt_secret_key(),
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        user_id = payload.get("sub")
        email = payload.get("email")

        # Check if user still exists in Redis
        user_data = await redis_client.get(f"user:{user_id}")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Generate new token
        new_token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "exp": datetime.utcnow() + timedelta(days=7)
            },
            get_jwt_secret_key(),
            algorithm="HS256"
        )

        return {
            "access_token": new_token,
            "token_type": "bearer"
        }

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )