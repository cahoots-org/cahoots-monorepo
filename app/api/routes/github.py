"""GitHub integration API endpoints."""

import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.storage import get_redis_client
from app.api.dependencies import require_feature

# Feature gate for GitHub integration
require_github = require_feature("github_integration")

router = APIRouter(prefix="/api/github", tags=["github"])


class GitHubConnectRequest(BaseModel):
    """Request model for connecting GitHub account."""
    access_token: str


# Simple in-memory storage for demo (in production, use database)
github_tokens: Dict[str, str] = {}


@router.get("/status")
async def get_github_status(
    current_user: dict = Depends(require_github),
) -> Dict[str, Any]:
    """Check if GitHub is connected and get user info.

    For now, checks environment variable. In production,
    would check per-user tokens in database.
    """
    # Check if there's a token configured
    env_token = os.getenv("GITHUB_TOKEN")

    if env_token:
        # Try to fetch user info with the token
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {env_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=5.0
                )

                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "connected": True,
                        "user": {
                            "login": user_data.get("login"),
                            "username": user_data.get("name", user_data.get("login")),
                            "public_repos": user_data.get("public_repos"),
                            "avatar_url": user_data.get("avatar_url")
                        }
                    }
        except Exception as e:
            print(f"Error checking GitHub status: {e}")

    return {
        "connected": False,
        "user": None
    }


@router.post("/connect")
async def connect_github(
    request: GitHubConnectRequest,
    current_user: dict = Depends(require_github),
) -> Dict[str, Any]:
    """Connect a GitHub account using personal access token.

    In production, this would store the token per-user in a database.
    For now, we set it as an environment variable for the session.
    """
    token = request.access_token.strip()

    if not token:
        raise HTTPException(status_code=400, detail="Access token is required")

    # Verify the token works by fetching user info
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10.0
            )

            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid GitHub token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API error: {response.text}"
                )

            user_data = response.json()

            # In production: Store token in database associated with user
            # For now: Set as environment variable (affects current process only)
            os.environ["GITHUB_TOKEN"] = token

            # Also store in Redis for persistence across requests
            try:
                redis = await get_redis_client()
                await redis.set("github_token", token, ex=86400)  # Expire after 24 hours
            except Exception as e:
                print(f"Could not store token in Redis: {e}")

            return {
                "success": True,
                "username": user_data.get("login"),
                "user": {
                    "login": user_data.get("login"),
                    "username": user_data.get("name", user_data.get("login")),
                    "public_repos": user_data.get("public_repos"),
                    "avatar_url": user_data.get("avatar_url")
                }
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GitHub API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to GitHub: {str(e)}")


@router.delete("/disconnect")
async def disconnect_github(
    current_user: dict = Depends(require_github),
) -> Dict[str, Any]:
    """Disconnect GitHub account.

    In production, this would remove the user's token from the database.
    """
    # Clear environment variable
    if "GITHUB_TOKEN" in os.environ:
        del os.environ["GITHUB_TOKEN"]

    # Clear from Redis
    try:
        redis = await get_redis_client()
        await redis.delete("github_token")
    except Exception as e:
        print(f"Could not clear token from Redis: {e}")

    return {
        "success": True,
        "message": "GitHub account disconnected"
    }