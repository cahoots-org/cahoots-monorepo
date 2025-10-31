"""Metrics endpoint for Prometheus."""

from fastapi import APIRouter
from fastapi.responses import Response
from app.metrics import get_metrics, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)
