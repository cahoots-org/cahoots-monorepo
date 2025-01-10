from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_project_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract project ID from bearer token."""
    # TODO: Implement proper token validation and project ID extraction
    return "test_project" 