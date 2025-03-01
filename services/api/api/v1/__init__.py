"""V1 API router initialization."""
from fastapi import APIRouter
from .auth import router as auth_router
from .projects import router as projects_router
from .teams import router as teams_router
from .billing import router as billing_router
from .health import router as health_router
from .organizations import router as organizations_router

# Create v1 router
router = APIRouter(prefix="/api/v1")

# Include all route modules
router.include_router(auth_router)
router.include_router(projects_router)
router.include_router(teams_router)
router.include_router(billing_router)
router.include_router(health_router)
router.include_router(organizations_router)

__all__ = ["router"] 