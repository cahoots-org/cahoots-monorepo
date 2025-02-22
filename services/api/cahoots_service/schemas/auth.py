"""Authentication schemas."""
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr

class PasswordReset(BaseModel):
    """Password reset schema."""
    token: str
    new_password: str

class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""
    token: str

class ResendVerificationRequest(BaseModel):
    """Resend verification request schema."""
    user_id: str

class SocialUserData(BaseModel):
    """Base social user data schema."""
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None

class GoogleUserData(SocialUserData):
    """Google user data schema."""
    locale: Optional[str] = None
    verified_email: Optional[bool] = None

class GithubUserData(SocialUserData):
    """GitHub user data schema."""
    login: str
    avatar_url: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None

class SocialLoginRequest(BaseModel):
    """Social login request schema."""
    provider: str
    user_data: Dict
    access_token: str  # The OAuth access token from the provider 