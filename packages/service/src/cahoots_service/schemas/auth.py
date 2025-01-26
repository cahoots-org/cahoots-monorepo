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

class SocialAuthRequest(BaseModel):
    """Social authentication request schema."""
    token: str
    provider_user_id: str
    provider_data: Dict

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