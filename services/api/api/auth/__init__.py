"""Authentication package."""
from .verify import verify_api_key, api_key_header, get_current_user
from .login import router as login_router
from .social import router as social_router
from fastapi import APIRouter

# Create a combined router
router = APIRouter()
router.include_router(login_router)
router.include_router(social_router)

__all__ = [
    'verify_api_key',
    'api_key_header',
    'router',
    'get_current_user'
] 