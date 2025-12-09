"""
Run management API routes.

Provides endpoints for managing test runs:
- Create and dispatch runs
- Get run status
- Get logs and results
- Cancel runs
"""

from fastapi import APIRouter, HTTPException, Depends, status

from app.models.schemas import (
    CreateRunRequest, CreateRunResponse,
    RunStatusResponse, RunLogsResponse,
    CancelRunResponse, RunStatus
)
from app.services.run_manager import RunManager
from app.api.dependencies import get_run_manager

router = APIRouter()


@router.post("", response_model=CreateRunResponse)
async def create_run(
    request: CreateRunRequest,
    run_manager: RunManager = Depends(get_run_manager)
):
    """
    Create and dispatch a new test run.

    The run is queued and dispatched to Cloud Run Jobs with sidecars.
    Returns a run_id for tracking.
    """
    run_id = await run_manager.create_run(request)

    # TODO: Get repo URL from workspace service
    # For now, construct from project_id
    repo_url = f"http://gitea:3000/cahoots-bot/{request.project_id}.git"

    # Start the run
    success = await run_manager.start_run(run_id, repo_url)

    if not success:
        run_status = await run_manager.get_status(run_id)
        return CreateRunResponse(
            run_id=run_id,
            status=run_status.status if run_status else RunStatus.ERROR
        )

    return CreateRunResponse(
        run_id=run_id,
        status=RunStatus.RUNNING
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager)
):
    """
    Get the status of a test run.

    Returns current status, exit code (if complete), and duration.
    """
    result = await run_manager.get_status(run_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}"
        )

    return result


@router.get("/{run_id}/logs", response_model=RunLogsResponse)
async def get_run_logs(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager)
):
    """
    Get logs and test results for a run.

    Returns stdout, stderr, and parsed test results.
    """
    result = await run_manager.get_logs(run_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}"
        )

    return result


@router.delete("/{run_id}", response_model=CancelRunResponse)
async def cancel_run(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager)
):
    """
    Cancel a running test run.

    Only pending and running runs can be cancelled.
    """
    success = await run_manager.cancel_run(run_id)

    return CancelRunResponse(
        run_id=run_id,
        cancelled=success
    )
