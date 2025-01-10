"""Federation schemas."""
from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class FederatedIdentityBase(BaseModel):
    """Base federated identity schema."""
    
    external_id: str = Field(
        ...,
        description="External identifier from provider"
    )
    provider_id: str = Field(
        ...,
        description="Federation provider ID"
    )
    attributes: Dict = Field(
        default_factory=dict,
        description="Identity attributes"
    )
    metadata: Optional[Dict] = Field(
        None,
        description="Additional metadata"
    )

class FederatedIdentityCreate(FederatedIdentityBase):
    """Schema for creating federated identity."""
    pass

class FederatedIdentityResponse(FederatedIdentityBase):
    """Schema for federated identity response."""
    
    id: str = Field(
        ...,
        description="Internal identity ID"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )

    class Config:
        """Pydantic config."""
        orm_mode = True

class TrustRelationshipBase(BaseModel):
    """Base trust relationship schema."""
    
    provider_id: str = Field(
        ...,
        description="Provider ID"
    )
    trusted_provider_id: str = Field(
        ...,
        description="Trusted provider ID"
    )
    trust_level: str = Field(
        "direct",
        description="Trust level (direct/transitive)"
    )
    valid_days: int = Field(
        365,
        description="Validity period in days"
    )
    metadata: Optional[Dict] = Field(
        None,
        description="Additional metadata"
    )

class TrustRelationshipCreate(TrustRelationshipBase):
    """Schema for creating trust relationship."""
    pass

class TrustRelationshipResponse(TrustRelationshipBase):
    """Schema for trust relationship response."""
    
    id: str = Field(
        ...,
        description="Relationship ID"
    )
    valid_from: datetime = Field(
        ...,
        description="Validity start timestamp"
    )
    valid_until: datetime = Field(
        ...,
        description="Validity end timestamp"
    )
    is_active: bool = Field(
        ...,
        description="Active status"
    )

    class Config:
        """Pydantic config."""
        orm_mode = True

class AttributeMappingBase(BaseModel):
    """Base attribute mapping schema."""
    
    provider_id: str = Field(
        ...,
        description="Provider ID"
    )
    source_attribute: str = Field(
        ...,
        description="Source attribute name"
    )
    target_attribute: str = Field(
        ...,
        description="Target attribute name"
    )
    transform_function: Optional[str] = Field(
        None,
        description="Optional transformation function"
    )
    is_required: bool = Field(
        False,
        description="Whether attribute is required"
    )

class AttributeMappingCreate(AttributeMappingBase):
    """Schema for creating attribute mapping."""
    pass

class AttributeMappingResponse(AttributeMappingBase):
    """Schema for attribute mapping response."""
    
    id: str = Field(
        ...,
        description="Mapping ID"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )

    class Config:
        """Pydantic config."""
        orm_mode = True 