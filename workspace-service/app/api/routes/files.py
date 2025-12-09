"""
File operations API routes.

Provides endpoints for agents to interact with workspace files:
- Read file content
- Write/create files
- Edit files (surgical replacement)
- List directory contents
- Search (grep) for patterns
- Delete files
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status

from app.models.schemas import (
    ReadFileRequest, ReadFileResponse,
    WriteFileRequest, WriteFileResponse,
    EditFileRequest, EditFileResponse,
    DeleteFileRequest, DeleteFileResponse,
    ListFilesRequest, ListFilesResponse,
    GrepRequest, GrepResponse
)
from app.services.workspace import WorkspaceService
from app.api.dependencies import get_workspace_service

router = APIRouter()


@router.post("/{project_id}/files/read", response_model=ReadFileResponse)
async def read_file(
    project_id: str,
    request: ReadFileRequest,
    branch: str = Query("main", description="Branch to read from"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Read the contents of a file from the workspace.

    Returns the file content or an error if the file doesn't exist.
    """
    result = await workspace.read_file(
        project_id=project_id,
        path=request.path,
        branch=branch
    )

    if not result.get("exists"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {request.path}"
        )

    return ReadFileResponse(
        content=result["content"],
        path=result["path"],
        exists=True
    )


@router.post("/{project_id}/files/write", response_model=WriteFileResponse)
async def write_file(
    project_id: str,
    request: WriteFileRequest,
    branch: str = Query("main", description="Branch to write to"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create or overwrite a file in the workspace.

    The file is automatically committed to the Git repository.
    """
    result = await workspace.write_file(
        project_id=project_id,
        path=request.path,
        content=request.content,
        message=request.message,
        branch=branch
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to write file")
        )

    return WriteFileResponse(
        ok=True,
        path=result["path"],
        commit=result["commit"]
    )


@router.post("/{project_id}/files/edit", response_model=EditFileResponse)
async def edit_file(
    project_id: str,
    request: EditFileRequest,
    branch: str = Query("main", description="Branch to edit in"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Make a surgical edit to an existing file by replacing text.

    The old_text must exist exactly once in the file.
    The change is automatically committed to the Git repository.
    """
    result = await workspace.edit_file(
        project_id=project_id,
        path=request.path,
        old_text=request.old_text,
        new_text=request.new_text,
        message=request.message,
        branch=branch
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to edit file")
        )

    return EditFileResponse(
        ok=True,
        path=result["path"],
        commit=result["commit"]
    )


@router.post("/{project_id}/files/delete", response_model=DeleteFileResponse)
async def delete_file(
    project_id: str,
    request: DeleteFileRequest,
    branch: str = Query("main", description="Branch to delete from"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Delete a file from the workspace.

    The deletion is automatically committed to the Git repository.
    """
    result = await workspace.delete_file(
        project_id=project_id,
        path=request.path,
        message=request.message,
        branch=branch
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Failed to delete file")
        )

    return DeleteFileResponse(
        ok=True,
        path=result["path"],
        commit=result["commit"]
    )


@router.post("/{project_id}/files/list", response_model=ListFilesResponse)
async def list_files(
    project_id: str,
    request: ListFilesRequest,
    branch: str = Query("main", description="Branch to list from"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    List files in a directory matching a pattern.

    Uses glob patterns (e.g., '*.ts', '**/*.py').
    """
    files = await workspace.list_files(
        project_id=project_id,
        path=request.path,
        pattern=request.pattern,
        branch=branch
    )

    return ListFilesResponse(
        files=files,
        path=request.path
    )


@router.post("/{project_id}/files/grep", response_model=GrepResponse)
async def grep_files(
    project_id: str,
    request: GrepRequest,
    branch: str = Query("main", description="Branch to search in"),
    workspace: WorkspaceService = Depends(get_workspace_service)
):
    """
    Search for a pattern in files.

    Supports regex patterns. Returns matching lines with file and line number.
    """
    matches = await workspace.grep(
        project_id=project_id,
        pattern=request.pattern,
        path=request.path,
        branch=branch
    )

    return GrepResponse(
        matches=matches,
        pattern=request.pattern,
        path=request.path
    )
