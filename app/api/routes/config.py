"""Configuration and status API endpoints."""

import os
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/status")
async def get_config_status() -> Dict[str, Any]:
    """Get configuration status for various integrations.

    Returns status of optional features so the frontend can
    enable/disable UI elements accordingly.
    """
    return {
        "github": {
            "enabled": bool(os.getenv("GITHUB_TOKEN")),
            "configured": bool(os.getenv("GITHUB_TOKEN")),
            "message": "GitHub integration requires GITHUB_TOKEN environment variable" if not os.getenv("GITHUB_TOKEN") else None
        },
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", "mock"),
            "configured": bool(
                os.getenv("OPENAI_API_KEY") or
                os.getenv("GROQ_API_KEY") or
                os.getenv("LAMBDA_API_KEY") or
                os.getenv("CEREBRAS_API_KEY") or
                os.getenv("LLM_PROVIDER") == "mock"
            )
        },
        "features": {
            "github_integration": bool(os.getenv("GITHUB_TOKEN")),
            "semantic_cache": os.getenv("USE_SEMANTIC_CACHE", "false").lower() == "true",
            "agentic_decomposition": bool(os.getenv("LAMBDA_API_KEY"))
        }
    }


@router.get("/environment")
async def get_environment() -> Dict[str, str]:
    """Get current environment information.

    Returns non-sensitive environment details.
    """
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
        "max_depth": os.getenv("MAX_DEPTH", "5"),
        "complexity_threshold": os.getenv("COMPLEXITY_THRESHOLD", "0.45"),
        "cache_ttl": os.getenv("CACHE_TTL", "3600")
    }