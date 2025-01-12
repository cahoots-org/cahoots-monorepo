"""Metrics endpoints."""
from fastapi import APIRouter, Response, Depends
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Optional
import logging

from src.api.auth import verify_api_key

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(tags=["metrics"])

@router.get("")
async def get_metrics(organization_id: str = Depends(verify_api_key)) -> Response:
    """Generate Prometheus metrics response.
    
    Returns:
        Response: FastAPI response containing Prometheus metrics
    """
    logger.debug("Generating metrics")
    metrics_data = generate_latest()
    logger.debug(f"Generated {len(metrics_data)} bytes of metrics data")
    
    response = Response(
        content=metrics_data,
        headers={"content-type": CONTENT_TYPE_LATEST}
    )
    logger.debug("Created metrics response")
    return response 