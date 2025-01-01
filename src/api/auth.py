from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, Security, status, Header
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from ..utils.config import config

class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token data model"""
    username: str
    scopes: List[str] = []
    exp: datetime

class User(BaseModel):
    """User model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: List[str] = []

class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "admin": "Full access to all operations",
        "read": "Read-only access",
        "write": "Write access",
    }
)

async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """Verify the API key from request header.
    
    Args:
        x_api_key: API key from request header
        
    Returns:
        str: The verified API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    if x_api_key != config.auth.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        config.auth.secret_key,
        algorithm=ALGORITHM
    )
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get current user from JWT token"""
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = jwt.decode(
            token,
            config.auth.secret_key,
            algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(
            username=username,
            scopes=token_scopes,
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
    except (JWTError, ValidationError):
        raise credentials_exception

    # Here you would typically look up the user in your database
    # For now, we'll use a mock user
    user = User(
        username=token_data.username,
        scopes=token_data.scopes
    )

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    return user

def get_current_active_user(
    current_user: User = Security(get_current_user, scopes=[])
) -> User:
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based security dependencies
def admin_user(
    current_user: User = Security(get_current_user, scopes=["admin"])
) -> User:
    """Require admin user"""
    return current_user

def read_access(
    current_user: User = Security(get_current_user, scopes=["read"])
) -> User:
    """Require read access"""
    return current_user

def write_access(
    current_user: User = Security(get_current_user, scopes=["write"])
) -> User:
    """Require write access"""
    return current_user 