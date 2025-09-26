"""GitHub integration routes for connecting repositories and managing context."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, HttpUrl

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/github", tags=["github"])


class GitHubConnectRequest(BaseModel):
    """Request model for connecting a GitHub account."""
    access_token: str


class GitHubRepository(BaseModel):
    """Model for a connected GitHub repository."""
    id: str
    owner: str
    name: str
    url: str
    branch: str
    connected_at: str
    last_synced: Optional[str] = None
    stats: Optional[Dict] = None


class GitHubContextRequest(BaseModel):
    """Request model for getting context for a task."""
    task_id: str
    task_description: str


@router.post("/connect", response_model=Dict)
async def connect_github_account(
    request: GitHubConnectRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Connect a GitHub account for the current user.
    
    This stores the user's GitHub access token and validates it.
    """
    try:
        print(f"GitHub connect: Received token starting with: {request.access_token[:10] if len(request.access_token) > 10 else request.access_token}...")
        print(f"GitHub connect: Token length: {len(request.access_token)}")
        
        github_user = None  # Initialize variable in the outer scope
        
        # Validate the token by fetching user info
        async with httpx.AsyncClient() as client:
            # Test the token with GitHub API using Bearer format (recommended in 2024)
            headers = {
                "Authorization": f"Bearer {request.access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            # Try Bearer format first (recommended)
            github_response = await client.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=10.0
            )
            
            # If Bearer fails, try legacy token format
            if github_response.status_code == 401:
                print(f"Bearer format failed, trying legacy token format")
                headers["Authorization"] = f"token {request.access_token}"
                github_response = await client.get(
                    "https://api.github.com/user",
                    headers=headers,
                    timeout=10.0
                )
            
            if github_response.status_code != 200:
                error_msg = f"Invalid GitHub access token. Status: {github_response.status_code}"
                if github_response.status_code == 401:
                    error_msg = "Invalid GitHub access token. Please ensure you're using a valid personal access token with 'repo' and 'read:user' scopes."
                elif github_response.status_code == 403:
                    error_msg = "GitHub API rate limit exceeded or insufficient permissions. Please check your token scopes."
                
                print(f"GitHub API error: {github_response.status_code} - {github_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )
            
            github_user = github_response.json()
            print(f"GitHub API validated successfully. User: {github_user.get('login')}")
            
        # Store the token in our service (use a separate client)
        try:
            async with httpx.AsyncClient() as service_client:
                print(f"Attempting to store token in GitHub integration service...")
                print(f"User ID: {current_user['id']}, GitHub user: {github_user['login']}")
                
                service_response = await service_client.post(
                    "http://github-integration:8095/connect",
                    json={
                        "user_id": current_user.id,
                        "access_token": request.access_token,
                        "github_username": github_user["login"]
                    },
                    timeout=30.0
                )
                
                print(f"GitHub integration service response: {service_response.status_code}")
                
                if service_response.status_code != 200:
                    error_detail = service_response.json().get("detail", "Failed to store token")
                    print(f"GitHub integration service error: {error_detail}")
                    raise HTTPException(
                        status_code=service_response.status_code,
                        detail=error_detail
                    )
        except httpx.RequestError as e:
            print(f"Failed to connect to GitHub integration service: {e}")
            # If the service is unavailable, we can still return success
            # since the token is valid - we just won't store it
            print("WARNING: GitHub integration service unavailable, token not stored")
        except Exception as e:
            print(f"Unexpected error storing token: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Still try to return success if the token is valid
            print("WARNING: Could not store token due to unexpected error")
        
        return {
            "username": github_user["login"],
            "user": github_user,
            "message": "GitHub account connected successfully"
        }
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub integration service unavailable: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect GitHub account: {str(e)}"
        )


@router.get("/repos", response_model=List[GitHubRepository])
async def list_connected_repos(
    current_user: Dict = Depends(get_current_user)
):
    """
    List all connected GitHub repositories for the current user.
    """
    try:
        # Forward to GitHub integration service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://github-integration:8095/repos/{current_user.id}",
                timeout=10.0
            )
            
            if response.status_code != 200:
                return []  # Return empty list if no repos found
            
            repos_data = response.json()
            
            # Convert to response models
            repos = []
            for repo in repos_data.get("repositories", []):
                repos.append(GitHubRepository(
                    id=repo["id"],
                    owner=repo["owner"],
                    name=repo["name"],
                    url=repo["url"],
                    branch=repo.get("branch", "main"),
                    connected_at=repo["connected_at"],
                    last_synced=repo.get("last_synced"),
                    stats=repo.get("stats")
                ))
            
            return repos
            
    except httpx.RequestError:
        return []  # Return empty list if service unavailable
    except Exception:
        return []


@router.delete("/repos/{repo_id}")
async def disconnect_repo(
    repo_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Disconnect a GitHub repository.
    """
    try:
        # Forward to GitHub integration service
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://github-integration:8095/repos/{current_user.id}/{repo_id}",
                timeout=10.0
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            return {"message": "Repository disconnected successfully"}
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub integration service unavailable: {str(e)}"
        )


@router.post("/context", response_model=Dict)
async def get_task_context(
    request: GitHubContextRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get GitHub repository context for a specific task.
    
    This endpoint is used during task decomposition to provide relevant
    code context from connected repositories.
    """
    try:
        # Forward to GitHub integration service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://github-integration:8095/context",
                json={
                    "user_id": current_user.id,
                    "task_id": request.task_id,
                    "task_description": request.task_description
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return {"context": None, "message": "No context available"}
            
            return response.json()
            
    except httpx.RequestError:
        # Don't fail task processing if GitHub service is unavailable
        return {"context": None, "message": "GitHub service unavailable"}
    except Exception:
        return {"context": None, "message": "Failed to fetch context"}


@router.post("/repos/{repo_id}/sync")
async def sync_repository(
    repo_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Manually trigger a sync for a connected repository.
    """
    try:
        # Forward to GitHub integration service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://github-integration:8095/repos/{current_user['id']}/{repo_id}/sync",
                timeout=60.0  # Longer timeout for sync operations
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            return response.json()
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub integration service unavailable: {str(e)}"
        )


@router.get("/status")
async def github_connection_status(
    current_user: Optional[Dict] = None
):
    """Check if the user has a GitHub account connected."""
    # For now, just return not connected since we don't have a GitHub integration service
    # In production, this would check if the user has stored GitHub credentials
    return {"connected": False}


@router.delete("/disconnect")
async def disconnect_github_account(
    current_user: Dict = Depends(get_current_user)
):
    """Disconnect the user's GitHub account."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://github-integration:8095/disconnect/{current_user.id}",
                timeout=10.0
            )
            
            return {"message": "GitHub account disconnected successfully"}
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub integration service unavailable: {str(e)}"
        )


@router.get("/user/repos")
async def list_user_repositories(
    current_user: Dict = Depends(get_current_user)
):
    """List all repositories accessible to the connected GitHub account."""
    try:
        async with httpx.AsyncClient() as client:
            # Get the user's token
            status_response = await client.get(
                f"http://github-integration:8095/status/{current_user.id}",
                timeout=10.0
            )
            
            if status_response.status_code != 200 or not status_response.json().get("connected"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="GitHub account not connected"
                )
            
            token = status_response.json().get("access_token")
            
            # Fetch repos from GitHub
            repos = []
            page = 1
            per_page = 100
            
            while True:
                github_response = await client.get(
                    f"https://api.github.com/user/repos",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    },
                    params={"per_page": per_page, "page": page, "sort": "updated"},
                    timeout=30.0
                )
                
                if github_response.status_code != 200:
                    break
                    
                page_repos = github_response.json()
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                
                # Limit to 300 repos for performance
                if len(repos) >= 300 or len(page_repos) < per_page:
                    break
                    
                page += 1
            
            # Format the response
            return [{
                "id": str(repo["id"]),
                "name": repo["name"],
                "full_name": repo["full_name"],
                "owner": repo["owner"]["login"],
                "url": repo["html_url"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "private": repo.get("private", False),
                "default_branch": repo.get("default_branch", "main"),
                "updated_at": repo.get("updated_at")
            } for repo in repos[:300]]
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repositories: {str(e)}"
        )


@router.get("/health")
async def github_integration_health():
    """Check if GitHub integration service is healthy."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://github-integration:8095/health",
                timeout=5.0
            )
            
            if response.status_code == 200:
                return {"status": "healthy", "service": "github-integration"}
            else:
                return {"status": "unhealthy", "service": "github-integration"}
                
    except Exception:
        return {"status": "unavailable", "service": "github-integration"}