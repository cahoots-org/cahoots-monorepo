"""Organization schemas."""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, UUID4, Field, ConfigDict

class Organization(BaseModel):
    """Organization model."""
    id: str
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    email: EmailStr
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass

class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    description: Optional[str] = None

class OrganizationResponse(BaseModel):
    """Organization response model."""
    id: str
    name: str
    description: Optional[str] = None
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS links")
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationsResponse(BaseModel):
    """Organizations list response model."""
    total: int = Field(..., description="Total number of organizations")
    organizations: List[OrganizationResponse] = Field(..., description="List of organizations")
    
    model_config = ConfigDict(from_attributes=True)

class MemberBase(BaseModel):
    """Base member schema."""
    email: EmailStr
    role: str = "member"

class MemberInvite(MemberBase):
    """Member invitation schema."""
    pass

class MemberUpdate(BaseModel):
    """Member update schema."""
    role: str

class MemberResponse(BaseModel):
    """Member response schema."""
    id: UUID4
    email: EmailStr
    full_name: str
    role: str
    joined_at: datetime
    last_active: Optional[datetime]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class OrganizationWithMembers(OrganizationResponse):
    """Organization response with members."""
    members: List[MemberResponse]

class TeamAssignment(BaseModel):
    """Team assignment schema."""
    team_id: UUID4

    model_config = ConfigDict(from_attributes=True)

class TeamResponse(BaseModel):
    """Team response schema."""
    id: UUID4
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS links")

    model_config = ConfigDict(from_attributes=True) 