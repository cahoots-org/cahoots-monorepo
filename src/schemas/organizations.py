"""Organization schemas."""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class OrganizationCreate(BaseModel):
    """Organization creation schema."""
    name: str = Field(..., description="Organization name")
    email: EmailStr = Field(..., description="Organization email")
    description: Optional[str] = Field(None, description="Organization description")

class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = Field(None, description="Organization name")
    email: Optional[EmailStr] = Field(None, description="Organization email")
    description: Optional[str] = Field(None, description="Organization description")

class OrganizationResponse(BaseModel):
    """Organization response schema."""
    id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    email: EmailStr = Field(..., description="Organization email")
    description: Optional[str] = Field(None, description="Organization description")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp") 