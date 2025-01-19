"""Login functionality."""
from typing import Dict, Any, Annotated
from fastapi import Depends, APIRouter, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import Optional

from src.core.dependencies import get_security_manager
from src.core.config import SecurityConfig
from src.utils.security import SecurityManager

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class LoginForm(BaseModel):
    """Form for handling login requests."""
    username: str
    password: str
    grant_type: str = "password"
    scope: str = ""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

@router.post("/token")
async def login(
    request: Request,
    security_config: SecurityConfig = Depends(),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> dict:
    """Login endpoint that returns an access token.
    
    Args:
        request: The request object containing form data
        security_config: Security configuration
        security_manager: Security manager instance
        
    Returns:
        dict: Access token response
        
    Raises:
        HTTPException: If authentication fails
    """
    form_data = await request.form()
    login_data = LoginForm(
        username=form_data.get("username"),
        password=form_data.get("password"),
        grant_type=form_data.get("grant_type", "password"),
        scope=form_data.get("scope", ""),
        client_id=form_data.get("client_id"),
        client_secret=form_data.get("client_secret")
    )
    
    scopes = login_data.scope.split()
    access_token = await security_manager.authenticate_user(
        login_data.username,
        login_data.password,
        scopes
    )
    return {"access_token": access_token, "token_type": "bearer"} 