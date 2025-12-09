"""
Git operations API routes.

Provides endpoints for repository and branch management:
- Create repository
- Create/merge branches
- Get repository status
- Get diffs
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status

from app.models.schemas import (
    CreateRepoRequest, CreateRepoResponse,
    CreateBranchRequest, CreateBranchResponse,
    MergeBranchRequest, MergeBranchResponse,
    CheckoutBranchRequest, CheckoutBranchResponse,
    RepoStatusResponse, DiffResponse,
    UpdateFromMainRequest, UpdateFromMainResponse,
    ResolveConflictRequest, ResolveConflictResponse
)
from app.services.workspace import WorkspaceService
from app.api.dependencies import get_workspace_service

router = APIRouter()


@router.post("/{project_id}/repo/create", response_model=CreateRepoResponse)
async def create_repository(
    project_id: str,
    request: CreateRepoRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a new repository for a project.

    The repository is created in Gitea with auto-init (README and main branch).
    """
    result = await workspace.create_repository(
        project_id=request.name,
        description=request.description or ""
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to create repository")
        )

    return CreateRepoResponse(
        ok=True,
        repo_url=result["repo_url"],
        clone_url=result["clone_url"],
        name=result["name"]
    )


@router.post("/{project_id}/branch/create", response_model=CreateBranchResponse)
async def create_branch(
    project_id: str,
    request: CreateBranchRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a new branch from an existing branch.

    Default: creates from 'main' branch.
    """
    try:
        result = await workspace.create_branch(
            project_id=project_id,
            branch_name=request.name,
            from_branch=request.from_branch
        )

        return CreateBranchResponse(
            ok=True,
            branch=result["branch"],
            from_branch=result["from_branch"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{project_id}/branch/merge", response_model=MergeBranchResponse)
async def merge_branch(
    project_id: str,
    request: MergeBranchRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Merge source branch into target branch.

    Supports different merge styles:
    - merge: Standard merge commit
    - rebase: Rebase and merge (linear history)
    - squash: Squash all commits into one

    Returns conflicts if the merge cannot be completed automatically.
    """
    result = await workspace.merge_branch(
        project_id=project_id,
        source=request.source,
        target=request.target,
        message=request.message,
        style=request.style.value
    )

    return MergeBranchResponse(
        ok=result.get("ok", False),
        commit=result.get("commit"),
        conflicts=result.get("conflicts")
    )


@router.get("/{project_id}/status", response_model=RepoStatusResponse)
async def get_status(
    project_id: str,
    branch: str = Query("main", description="Branch to check status of"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Get repository status.

    Returns current branch, last commit info, and any uncommitted changes.
    """
    result = await workspace.get_status(
        project_id=project_id,
        branch=branch
    )

    return RepoStatusResponse(
        branch=result["branch"],
        clean=result["clean"],
        last_commit=result["last_commit"],
        last_commit_message=result["last_commit_message"],
        uncommitted_files=result["uncommitted_files"]
    )


@router.get("/{project_id}/diff", response_model=DiffResponse)
async def get_diff(
    project_id: str,
    base: str = Query("main", description="Base ref for diff"),
    head: str = Query("HEAD", description="Head ref for diff"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Get diff between two refs (branches, commits, or tags).
    """
    result = await workspace.get_diff(
        project_id=project_id,
        base=base,
        head=head
    )

    return DiffResponse(
        diff=result["diff"],
        files_changed=result["files_changed"]
    )


@router.post("/{project_id}/branch/update-from-main", response_model=UpdateFromMainResponse)
async def update_branch_from_main(
    project_id: str,
    request: UpdateFromMainRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Update a feature branch by merging main into it.

    This pulls the latest changes from main into the feature branch.
    If there are conflicts, returns them in the response with has_conflicts=True.

    Used by MergeAgent to ensure feature branches are up-to-date before merging to main.
    """
    result = await workspace.update_branch_from_main(
        project_id=project_id,
        branch=request.branch
    )

    if result.get("has_conflicts"):
        return UpdateFromMainResponse(
            ok=False,
            has_conflicts=True,
            conflicts=result.get("conflicts", []),
            message=result.get("message")
        )

    return UpdateFromMainResponse(
        ok=result.get("ok", True),
        has_conflicts=False,
        commit=result.get("commit"),
        message=result.get("message")
    )


@router.post("/{project_id}/branch/resolve-conflict", response_model=ResolveConflictResponse)
async def resolve_conflict(
    project_id: str,
    request: ResolveConflictRequest,
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Resolve a merge conflict by providing the resolved file content.

    After all conflicts are resolved, the merge can be completed.
    Returns the list of remaining conflicts (empty if all resolved).
    """
    result = await workspace.resolve_conflict(
        project_id=project_id,
        branch=request.branch,
        path=request.path,
        resolved_content=request.resolved_content,
        message=request.message
    )

    return ResolveConflictResponse(
        ok=result.get("ok", True),
        commit=result.get("commit"),
        remaining_conflicts=result.get("remaining_conflicts", [])
    )
