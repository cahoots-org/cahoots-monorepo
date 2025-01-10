"""SAML configuration schemas."""
from typing import Dict, Optional
from pydantic import BaseModel, Field, HttpUrl

class SAMLConfig(BaseModel):
    """SAML configuration settings."""
    
    entity_id: str = Field(
        ...,
        description="Unique identifier for this service provider"
    )
    cert_path: str = Field(
        ...,
        description="Path to X.509 certificate file"
    )
    private_key_path: str = Field(
        ...,
        description="Path to private key file"
    )
    want_assertions_signed: bool = Field(
        True,
        description="Whether to require signed assertions"
    )
    want_response_signed: bool = Field(
        True,
        description="Whether to require signed responses"
    )
    allow_idp_initiated: bool = Field(
        False,
        description="Whether to allow IdP-initiated SSO"
    )
    signing_algorithm: str = Field(
        "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        description="XML signature algorithm"
    )
    digest_algorithm: str = Field(
        "http://www.w3.org/2001/04/xmlenc#sha256",
        description="XML digest algorithm"
    )

class IdentityProviderConfig(BaseModel):
    """Identity provider configuration."""
    
    name: str = Field(
        ...,
        description="Display name for the identity provider"
    )
    description: Optional[str] = Field(
        None,
        description="Optional description"
    )
    entity_id: str = Field(
        ...,
        description="Entity ID from provider metadata"
    )
    sso_url: HttpUrl = Field(
        ...,
        description="Single Sign-On service URL"
    )
    slo_url: Optional[HttpUrl] = Field(
        None,
        description="Single Logout service URL"
    )
    certificate: str = Field(
        ...,
        description="X.509 certificate for signature validation"
    )
    attribute_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of SAML attributes to user fields"
    )
    force_authn: bool = Field(
        False,
        description="Whether to force re-authentication"
    )
    name_id_format: str = Field(
        "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        description="Name ID format to request"
    ) 