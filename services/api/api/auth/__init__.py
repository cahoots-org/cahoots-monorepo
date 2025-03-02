"""Authentication package."""

from fastapi import APIRouter

from .login import router as login_router
from .social import router as social_router
from .verify import api_key_header, get_current_user, verify_api_key

# Create a combined router
router = APIRouter()
router.include_router(login_router)
router.include_router(social_router)

__all__ = ["verify_api_key", "api_key_header", "router", "get_current_user"]
