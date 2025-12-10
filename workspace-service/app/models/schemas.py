"""Pydantic schemas for Workspace Service API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# File Operations
# ============================================================================

class ReadFileRequest(BaseModel):
    """Request to read a file."""
    path: str = Field(..., description="Relative path to the file (e.g., 'src/handlers/auth.ts')")


class ReadFileResponse(BaseModel):
    """Response containing file content."""
    content: str
    path: str
    exists: bool = True


class WriteFileRequest(BaseModel):
    """Request to write/create a file."""
    path: str = Field(..., description="Relative path for the file")
    content: str = Field(..., description="Full content to write to the file")
    message: Optional[str] = Field(None, description="Commit message (auto-generated if not provided)")


class WriteFileResponse(BaseModel):
    """Response after writing a file."""
    ok: bool
    path: str
    commit: str = Field(..., description="Git commit SHA")


class EditFileRequest(BaseModel):
    """Request to surgically edit a file."""
    path: str = Field(..., description="Relative path to the file")
    old_text: str = Field(..., alias="old", description="Exact text to find and replace")
    new_text: str = Field(..., alias="new", description="Text to replace it with")
    message: Optional[str] = Field(None, description="Commit message (auto-generated if not provided)")

    class Config:
        populate_by_name = True


class EditFileResponse(BaseModel):
    """Response after editing a file."""
    ok: bool
    path: str
    commit: str


class DeleteFileRequest(BaseModel):
    """Request to delete a file."""
    path: str = Field(..., description="Relative path to the file to delete")
    message: Optional[str] = Field(None, description="Commit message")


class DeleteFileResponse(BaseModel):
    """Response after deleting a file."""
    ok: bool
    path: str
    commit: str


class ListFilesRequest(BaseModel):
    """Request to list files in a directory."""
    path: str = Field(".", description="Directory path to list")
    pattern: str = Field("*", description="Glob pattern to filter files (e.g., '*.ts')")


class ListFilesResponse(BaseModel):
    """Response containing file list."""
    files: List[str]
    path: str


class GrepRequest(BaseModel):
    """Request to search for patterns in files."""
    pattern: str = Field(..., description="Regex pattern to search for")
    path: str = Field(".", description="Directory to search in")


class GrepMatch(BaseModel):
    """A single grep match."""
    file: str
    line: int
    content: str


class GrepResponse(BaseModel):
    """Response containing grep matches."""
    matches: List[GrepMatch]
    pattern: str
    path: str


# ============================================================================
# Git Operations
# ============================================================================

class CreateRepoRequest(BaseModel):
    """Request to create a new repository."""
    name: str = Field(..., description="Repository name")
    description: Optional[str] = Field("", description="Repository description")
    private: bool = Field(True, description="Whether the repo is private")


class CreateRepoResponse(BaseModel):
    """Response after creating a repository."""
    ok: bool
    repo_url: str
    clone_url: str
    name: str


class CreateBranchRequest(BaseModel):
    """Request to create a new branch."""
    name: str = Field(..., description="Branch name to create")
    from_branch: str = Field("main", alias="from", description="Branch to create from")

    class Config:
        populate_by_name = True


class CreateBranchResponse(BaseModel):
    """Response after creating a branch."""
    ok: bool
    branch: str
    from_branch: str


class MergeStyle(str, Enum):
    """Git merge strategy."""
    merge = "merge"
    rebase = "rebase"
    squash = "squash"


class MergeBranchRequest(BaseModel):
    """Request to merge branches."""
    source: str = Field(..., description="Source branch to merge from")
    target: str = Field("main", description="Target branch to merge into")
    message: Optional[str] = Field(None, description="Merge commit message")
    style: MergeStyle = Field(MergeStyle.merge, description="Merge style: merge, rebase, or squash")


class MergeBranchResponse(BaseModel):
    """Response after merging branches."""
    ok: bool
    commit: Optional[str] = None
    conflicts: Optional[List[str]] = None


class CheckoutBranchRequest(BaseModel):
    """Request to checkout a branch."""
    branch: str = Field(..., description="Branch to checkout")


class CheckoutBranchResponse(BaseModel):
    """Response after checkout."""
    ok: bool
    branch: str


class RepoStatusResponse(BaseModel):
    """Repository status response."""
    branch: str
    clean: bool
    last_commit: str
    last_commit_message: str
    uncommitted_files: List[str] = []


class DiffResponse(BaseModel):
    """Diff between branches or commits."""
    diff: str
    files_changed: List[str]


class UpdateFromMainRequest(BaseModel):
    """Request to update a branch from main (pull main into feature branch)."""
    branch: str = Field(..., description="Feature branch to update")


class UpdateFromMainResponse(BaseModel):
    """Response after updating from main."""
    ok: bool
    has_conflicts: bool = False
    conflicts: Optional[List[str]] = None
    commit: Optional[str] = None
    message: Optional[str] = None


class ResolveConflictRequest(BaseModel):
    """Request to resolve a conflict in a file."""
    branch: str = Field(..., description="Branch with the conflict")
    path: str = Field(..., description="File path with conflict")
    resolved_content: str = Field(..., description="Resolved file content")
    message: Optional[str] = Field(None, description="Commit message")


class ResolveConflictResponse(BaseModel):
    """Response after resolving a conflict."""
    ok: bool
    commit: Optional[str] = None
    remaining_conflicts: List[str] = []


# ============================================================================
# GitHub Integration (Paid Feature)
# ============================================================================

class GitHubImportRequest(BaseModel):
    """Request to import a GitHub repository."""
    repo_url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/user/repo)")
    branch: str = Field("main", description="Branch to import")


class GitHubImportResponse(BaseModel):
    """Response after importing a GitHub repository."""
    ok: bool
    files_indexed: int
    repo_name: str
    local_repo_url: str


class GitHubPushRequest(BaseModel):
    """Request to push changes to GitHub."""
    branch: str = Field(..., description="Branch to push")


class GitHubPushResponse(BaseModel):
    """Response after pushing to GitHub."""
    ok: bool
    commits_pushed: int


class GitHubPRRequest(BaseModel):
    """Request to create a GitHub pull request."""
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    branch: str = Field(..., description="Branch with changes")
    base: str = Field("main", description="Base branch to merge into")


class GitHubPRResponse(BaseModel):
    """Response after creating a GitHub PR."""
    ok: bool
    pr_url: str
    pr_number: int


# ============================================================================
# AST Metadata
# ============================================================================

class ASTMetadata(BaseModel):
    """Extracted AST metadata from source code."""
    functions: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    types: List[str] = Field(default_factory=list)


class FileMetadata(BaseModel):
    """Full file metadata for Context Engine."""
    path: str
    content: str
    language: str
    ast_metadata: Optional[ASTMetadata] = None
    commit: Optional[str] = None
    last_modified: Optional[datetime] = None


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_type: Optional[str] = None
