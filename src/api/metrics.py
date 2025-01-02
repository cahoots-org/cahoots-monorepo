from fastapi import Response
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_metrics() -> Response:
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