from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserRole(BaseModel):
    """User role within an organization."""
    
    organization_id: str = Field(..., description="Organization ID this role applies to")
    role: str = Field(..., description="Role name (admin, member, viewer)")
    permissions: List[str] = Field(default_factory=list, description="List of permissions")

class User(BaseModel):
    """User model with role-based access control."""
    
    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    hashed_password: str = Field(..., description="Hashed password")
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_verified: bool = Field(default=False, description="Whether email is verified")
    organizations: List[UserRole] = Field(default_factory=list, description="Organizations and roles")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    preferences: dict = Field(
        default_factory=lambda: {
            "notification_settings": {
                "email": True,
                "in_app": True
            },
            "theme": "light"
        }
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "user123",
                "username": "testuser",
                "email": "test@example.com"
            }
        }
    ) 