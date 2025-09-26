"""Authentication dependencies for FastAPI."""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError

# Security scheme
security = HTTPBearer(auto_error=False)

# Get JWT settings from environment
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Get the current user from the JWT token.

    In production: Validates JWT token
    In development: Allows dev-bypass-token
    """
    environment = os.environ.get("ENVIRONMENT", "development")

    # No credentials provided
    if not credentials:
        if environment == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Development mode - allow anonymous access
            return {"id": "dev-user", "email": "dev@localhost"}

    token = credentials.credentials

    # Development bypass token (only in non-production)
    if environment != "production" and token == "dev-bypass-token":
        return {"id": "dev-user", "email": "dev@localhost"}

    # Validate JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"id": user_id, "email": email}

    except (InvalidTokenError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(environment: str = None) -> bool:
    """
    Check if authentication is required based on environment.

    Returns True if auth is required (production), False otherwise.
    """
    if environment is None:
        environment = os.environ.get("ENVIRONMENT", "development")

    return environment == "production"