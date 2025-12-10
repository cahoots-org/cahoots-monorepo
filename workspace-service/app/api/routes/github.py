"""
GitHub integration API routes (Paid Feature).

Provides endpoints for:
- Importing existing GitHub repositories
- Pushing changes back to GitHub
- Creating pull requests
"""

from fastapi import APIRouter, HTTPException, Depends, status

from app.models.schemas import (
    GitHubImportRequest, GitHubImportResponse,
    GitHubPushRequest, GitHubPushResponse,
    GitHubPRRequest, GitHubPRResponse
)
from app.services.workspace import WorkspaceService
from app.api.dependencies import get_workspace_service

router = APIRouter()


@router.post("/{project_id}/github/import", response_model=GitHubImportResponse)
async def import_github_repo(
    project_id: str,
    request: GitHubImportRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Import a GitHub repository.

    Clones the repository to Gitea and indexes all files for the Context Engine.
    This is a PAID FEATURE.
    """
    # TODO: Implement GitHub import
    # 1. Validate GitHub OAuth token
    # 2. Clone repo to Gitea
    # 3. Parse all files with AST
    # 4. Generate embeddings for Context Engine
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GitHub import is a paid feature - coming soon"
    )


@router.post("/{project_id}/github/push", response_model=GitHubPushResponse)
async def push_to_github(
    project_id: str,
    request: GitHubPushRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Push changes to the connected GitHub repository.

    This is a PAID FEATURE.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GitHub push is a paid feature - coming soon"
    )


@router.post("/{project_id}/github/pr", response_model=GitHubPRResponse)
async def create_github_pr(
    project_id: str,
    request: GitHubPRRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a pull request on the connected GitHub repository.

    This is a PAID FEATURE.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GitHub PR creation is a paid feature - coming soon"
    )
