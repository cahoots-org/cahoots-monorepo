from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    generate_latest,
    multiprocess,
)
from typing import Optional
import os

router = APIRouter()

# Initialize the registry
registry = CollectorRegistry(auto_describe=True)

@router.get("/metrics")
def get_metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    ) 