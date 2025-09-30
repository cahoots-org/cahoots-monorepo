"""Google OAuth 2.0 Authentication Routes

This module implements a complete, robust Google OAuth 2.0 flow with:
- Proper error handling and logging
- Resilient HTTP client with retries
- Clear separation of concerns
- Comprehensive validation
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode
import secrets
import hashlib
import re

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, validator
import httpx
import jwt

from app.api.dependencies import get_redis_client
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(prefix="/api/auth", tags=["auth"])

# ==================== Configuration ====================

class OAuthConfig:
    """Centralized OAuth configuration"""

    @staticmethod
    def get_environment() -> str:
        return os.environ.get("ENVIRONMENT", "development")

    @staticmethod
    def get_google_client_id() -> Optional[str]:
        return os.environ.get("GOOGLE_CLIENT_ID")

    @staticmethod
    def get_google_client_secret() -> Optional[str]:
        return os.environ.get("GOOGLE_CLIENT_SECRET")

    @staticmethod
    def get_jwt_secret() -> str:
        # In production, this should be a strong, unique secret
        return os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")

    @staticmethod
    def get_frontend_url() -> str:
        if OAuthConfig.get_environment() == "production":
            return "https://cahoots-frontend.fly.dev"
        return "http://localhost:3000"

    @staticmethod
    def get_redirect_uri() -> str:
        """Get the OAuth callback URL that Google will redirect to"""
        if OAuthConfig.get_environment() == "production":
            return "https://cahoots-frontend.fly.dev/oauth/google/callback"
        return "http://localhost:3000/oauth/google/callback"

    @staticmethod
    def get_google_auth_url() -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @staticmethod
    def get_google_token_url() -> str:
        return "https://oauth2.googleapis.com/token"

    @staticmethod
    def get_google_userinfo_url() -> str:
        return "https://www.googleapis.com/oauth2/v3/userinfo"

# ==================== Data Models ====================

class AuthorizeResponse(BaseModel):
    """Response for the authorization endpoint"""
    redirect_uri: str = Field(..., description="The Google OAuth authorization URL")
    state: str = Field(..., description="State parameter for CSRF protection")

class ExchangeRequest(BaseModel):
    """Request body for exchanging authorization code"""
    code: str = Field(..., description="The authorization code from Google")
    state: Optional[str] = Field(None, description="Optional state for validation")

class TokenResponse(BaseModel):
    """Response after successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=86400, description="Token expiration in seconds")
    user: Dict[str, Any] = Field(..., description="User information")

class UserInfo(BaseModel):
    """User information from Google"""
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str = "google"

class RegisterRequest(BaseModel):
    """Request body for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: Optional[str] = Field(None, description="User's full name")

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        return v

class LoginRequest(BaseModel):
    """Request body for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

# ==================== Password Utilities ====================

class PasswordHasher:
    """Secure password hashing utility"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return f"{salt}${password_hash}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verify a password against a stored hash"""
        try:
            salt, hash_part = stored_hash.split('$')
            password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
            return password_hash == hash_part
        except Exception:
            return False

# ==================== HTTP Client ====================

class ResilientHTTPClient:
    """HTTP client with retry logic and proper error handling"""

    @staticmethod
    async def post(url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Make a POST request with retries"""
        max_retries = 3
        timeout = httpx.Timeout(30.0, connect=10.0)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.post(url, data=data, headers=headers or {})
                    response.raise_for_status()
                    return response
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Request to Google timed out"
                    )
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} from {url}: {e.response.text}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Google OAuth error: {e.response.text}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Unable to connect to Google OAuth service"
                    )

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    @staticmethod
    async def get(url: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Make a GET request with retries"""
        max_retries = 3
        timeout = httpx.Timeout(30.0, connect=10.0)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers or {})
                    response.raise_for_status()
                    return response
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Request to Google timed out"
                    )
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} from {url}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Google API error: {e.response.status_code}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Unable to connect to Google API"
                    )

            # Wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

# ==================== Auth Endpoints ====================

@router.get("/google/authorize", response_model=AuthorizeResponse)
async def google_authorize():
    """
    Step 1: Generate Google OAuth authorization URL

    This endpoint creates the URL that the frontend should redirect users to
    for Google authentication.
    """
    client_id = OAuthConfig.get_google_client_id()
    if not client_id:
        logger.error("Google Client ID not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured. Please set GOOGLE_CLIENT_ID."
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build authorization URL with all required parameters
    params = {
        "client_id": client_id,
        "redirect_uri": OAuthConfig.get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent screen
        "state": state
    }

    auth_url = f"{OAuthConfig.get_google_auth_url()}?{urlencode(params)}"

    logger.info(f"Generated auth URL for client_id: {client_id[:10]}...")
    logger.info(f"Redirect URI: {OAuthConfig.get_redirect_uri()}")

    return AuthorizeResponse(redirect_uri=auth_url, state=state)


@router.post("/google/exchange", response_model=TokenResponse)
async def google_exchange(
    request: ExchangeRequest,
    redis_client = Depends(get_redis_client)
):
    """
    Step 2: Exchange authorization code for tokens

    This endpoint receives the authorization code from the frontend and
    exchanges it for an access token, then fetches user info and creates
    a session.
    """
    import asyncio  # Import here to use in retry logic

    logger.info(f"Starting OAuth exchange for code: {request.code[:10]}...")

    # Validate configuration
    client_id = OAuthConfig.get_google_client_id()
    client_secret = OAuthConfig.get_google_client_secret()

    if not client_id or not client_secret:
        logger.error("OAuth credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )

    # Exchange authorization code for tokens
    try:
        token_data = {
            "code": request.code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": OAuthConfig.get_redirect_uri(),
            "grant_type": "authorization_code"
        }

        logger.info(f"Exchanging code with redirect_uri: {OAuthConfig.get_redirect_uri()}")

        response = await ResilientHTTPClient.post(
            OAuthConfig.get_google_token_url(),
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        tokens = response.json()
        access_token = tokens.get("access_token")

        if not access_token:
            logger.error(f"No access token in response: {tokens}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid response from Google OAuth"
            )

        logger.info("Successfully obtained access token")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to exchange code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )

    # Fetch user information
    try:
        user_response = await ResilientHTTPClient.get(
            OAuthConfig.get_google_userinfo_url(),
            headers={"Authorization": f"Bearer {access_token}"}
        )

        user_data = user_response.json()

        if not user_data.get("sub"):
            logger.error(f"Invalid user data: {user_data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user information from Google"
            )

        logger.info(f"Successfully fetched user info for: {user_data.get('email', 'unknown')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch user information: {str(e)}"
        )

    # Create user object
    user = UserInfo(
        id=f"google_{user_data['sub']}",
        email=user_data.get("email", ""),
        name=user_data.get("name"),
        picture=user_data.get("picture"),
        provider="google"
    )

    # Store user in Redis (24 hour TTL)
    user_dict = user.dict()
    user_dict["created_at"] = datetime.utcnow().isoformat()

    try:
        await redis_client.set(
            f"user:{user.id}",
            user_dict,
            expire=86400  # 24 hours
        )
        logger.info(f"Stored user in Redis: {user.id}")
    except Exception as e:
        logger.error(f"Failed to store user in Redis: {str(e)}")
        # Continue anyway - user can still authenticate

    # Generate JWT token
    jwt_payload = {
        "sub": user.id,
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(days=1),
        "iat": datetime.utcnow(),
        "iss": "cahoots"
    }

    jwt_token = jwt.encode(
        jwt_payload,
        OAuthConfig.get_jwt_secret(),
        algorithm="HS256"
    )

    logger.info(f"OAuth flow completed successfully for {user.email}")

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        expires_in=86400,
        user=user_dict
    )


@router.get("/me")
async def get_current_user(
    request: Request,
    redis_client = Depends(get_redis_client)
):
    """
    Get current authenticated user from JWT token
    """
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token,
            OAuthConfig.get_jwt_secret(),
            algorithms=["HS256"]
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Try to get user from Redis
        user_data = await redis_client.get(f"user:{user_id}")

        if user_data:
            return user_data

        # If not in Redis, return basic info from token
        return {
            "id": user_id,
            "email": payload.get("email"),
            "provider": "google"
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /me endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    redis_client = Depends(get_redis_client)
):
    """
    Register a new user with email and password
    """
    logger.info(f"Registration attempt for email: {request.email}")

    # Check if user already exists
    existing_user = await redis_client.get(f"user:email:{request.email}")
    if existing_user:
        logger.warning(f"Registration failed: Email {request.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Generate user ID
    user_id = f"local_{secrets.token_urlsafe(16)}"

    # Hash password
    password_hash = PasswordHasher.hash_password(request.password)

    # Create user object
    user_data = {
        "id": user_id,
        "email": request.email,
        "name": request.name or request.email.split('@')[0],
        "picture": None,
        "provider": "local",
        "password_hash": password_hash,
        "created_at": datetime.utcnow().isoformat()
    }

    # Store user in Redis
    try:
        # Store by user ID
        await redis_client.set(
            f"user:{user_id}",
            user_data,
            expire=None  # No expiration for user accounts
        )

        # Store email-to-ID mapping
        await redis_client.set(
            f"user:email:{request.email}",
            user_id,
            expire=None
        )

        logger.info(f"User registered successfully: {user_id}")

    except Exception as e:
        logger.error(f"Failed to store user in Redis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

    # Generate JWT token
    jwt_payload = {
        "sub": user_id,
        "email": request.email,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
        "iss": "cahoots"
    }

    jwt_token = jwt.encode(
        jwt_payload,
        OAuthConfig.get_jwt_secret(),
        algorithm="HS256"
    )

    # Remove password_hash from response
    user_response = {k: v for k, v in user_data.items() if k != 'password_hash'}

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        expires_in=604800,  # 7 days
        user=user_response
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    redis_client = Depends(get_redis_client)
):
    """
    Login with email and password
    """
    logger.info(f"Login attempt for email: {request.email}")

    # Get user ID from email
    user_id = await redis_client.get(f"user:email:{request.email}")
    if not user_id:
        logger.warning(f"Login failed: Email {request.email} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Get user data
    user_data = await redis_client.get(f"user:{user_id}")
    if not user_data:
        logger.error(f"User data not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is a local account
    if user_data.get("provider") != "local":
        logger.warning(f"Login failed: User {request.email} uses OAuth provider")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please login with {user_data.get('provider', 'OAuth provider')}"
        )

    # Verify password
    password_hash = user_data.get("password_hash")
    if not password_hash or not PasswordHasher.verify_password(request.password, password_hash):
        logger.warning(f"Login failed: Invalid password for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Generate JWT token
    jwt_payload = {
        "sub": user_id,
        "email": request.email,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
        "iss": "cahoots"
    }

    jwt_token = jwt.encode(
        jwt_payload,
        OAuthConfig.get_jwt_secret(),
        algorithm="HS256"
    )

    # Remove password_hash from response
    user_response = {k: v for k, v in user_data.items() if k != 'password_hash'}

    logger.info(f"Login successful for {request.email}")

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        expires_in=604800,  # 7 days
        user=user_response
    )


@router.post("/logout")
async def logout(
    request: Request,
    redis_client = Depends(get_redis_client)
):
    """
    Logout user by removing session from Redis
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return {"message": "Already logged out"}

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            OAuthConfig.get_jwt_secret(),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")

        if user_id:
            # For session-based logout, we could invalidate the token
            # For now, just log the action
            logger.info(f"User {user_id} logged out")

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return {"message": "Logout completed"}


@router.get("/test-connections")
async def test_connections(redis_client = Depends(get_redis_client)):
    """Test external connections and Redis to diagnose issues"""
    results = {}

    # Test Google connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://accounts.google.com")
            results["google"] = {"status": "success", "code": response.status_code}
    except Exception as e:
        results["google"] = {"status": "error", "message": str(e)}

    # Test Redis connection
    try:
        await redis_client.ping()
        results["redis"] = {"status": "success"}
    except Exception as e:
        results["redis"] = {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    # Test OAuth2 token endpoint
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={"test": "test"}
            )
            results["oauth_endpoint"] = {"status": "success", "code": response.status_code}
    except Exception as e:
        results["oauth_endpoint"] = {"status": "error", "message": str(e)}

    return results

@router.get("/health")
async def auth_health():
    """
    Health check for auth service
    """
    config_status = {
        "google_client_id": bool(OAuthConfig.get_google_client_id()),
        "google_client_secret": bool(OAuthConfig.get_google_client_secret()),
        "environment": OAuthConfig.get_environment(),
        "redirect_uri": OAuthConfig.get_redirect_uri()
    }

    return {
        "status": "healthy",
        "config": config_status
    }