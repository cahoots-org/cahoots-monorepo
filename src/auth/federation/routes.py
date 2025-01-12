"""Federation management routes."""
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session
from src.services.federation import FederationService
from src.auth.federation.base import FederatedIdentity
from src.models.federation import (
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)
from src.schemas.federation import (
    FederatedIdentityCreate,
    TrustRelationshipCreate,
    AttributeMappingCreate
)
from src.core.dependencies import ServiceDeps

router = APIRouter(prefix="/federation", tags=["federation"])

async def get_federation_service(
    deps: ServiceDeps = Depends()
) -> FederationService:
    """Get federation service instance."""
    service = FederationService(deps=deps)
    await service.initialize()
    return service

@router.post("/identities")
async def link_federated_identity(
    identity: FederatedIdentityCreate,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Link federated identity to user.
    
    Args:
        identity: Federated identity data
        service: Federation service
        
    Returns:
        Dict: Success response
    """
    federated_identity = FederatedIdentity(
        external_id=identity.external_id,
        provider_id=identity.provider_id,
        attributes=identity.attributes,
        metadata=identity.metadata
    )
    
    success = await service.link_identity(identity.user_id, federated_identity)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity already linked"
        )
    
    return {"status": "success"}

@router.delete("/identities/{mapping_id}")
async def unlink_federated_identity(
    mapping_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Unlink federated identity.
    
    Args:
        mapping_id: Mapping ID
        service: Federation service
        
    Returns:
        Dict: Success response
    """
    success = await service.unlink_identity(mapping_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not found"
        )
    
    return {"status": "success"}

@router.post("/trust")
async def establish_trust_relationship(
    relationship: TrustRelationshipCreate,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Establish trust relationship between providers.
    
    Args:
        relationship: Trust relationship data
        service: Federation service
        
    Returns:
        Dict: Created relationship
    """
    trust = await service.establish_trust(
        provider_id=relationship.provider_id,
        trusted_provider_id=relationship.trusted_provider_id,
        trust_level=relationship.trust_level,
        valid_days=relationship.valid_days,
        metadata=relationship.metadata
    )
    
    return {
        "id": str(trust.id),
        "provider_id": str(trust.provider_id),
        "trusted_provider_id": str(trust.trusted_provider_id),
        "trust_level": trust.trust_level,
        "valid_from": trust.valid_from.isoformat(),
        "valid_until": trust.valid_until.isoformat()
    }

@router.delete("/trust/{relationship_id}")
async def revoke_trust_relationship(
    relationship_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Revoke trust relationship.
    
    Args:
        relationship_id: Relationship ID
        service: Federation service
        
    Returns:
        Dict: Success response
    """
    success = await service.revoke_trust(relationship_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trust relationship not found"
        )
    
    return {"status": "success"}

@router.get("/trust/validate")
async def validate_trust_relationship(
    provider_id: str,
    trusted_provider_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Validate trust between providers.
    
    Args:
        provider_id: Provider ID
        trusted_provider_id: Trusted provider ID
        service: Federation service
        
    Returns:
        Dict: Trust status
    """
    is_trusted = await service.validate_trust(provider_id, trusted_provider_id)
    return {"trusted": is_trusted}

@router.post("/attributes/mapping")
async def create_attribute_mapping(
    mapping: AttributeMappingCreate,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Create attribute mapping.
    
    Args:
        mapping: Attribute mapping data
        service: Federation service
        
    Returns:
        Dict: Created mapping
    """
    attr_mapping = await service.create_attribute_mapping(
        provider_id=mapping.provider_id,
        source_attribute=mapping.source_attribute,
        target_attribute=mapping.target_attribute,
        transform_function=mapping.transform_function,
        is_required=mapping.is_required
    )
    
    return {
        "id": str(attr_mapping.id),
        "provider_id": str(attr_mapping.provider_id),
        "source_attribute": attr_mapping.source_attribute,
        "target_attribute": attr_mapping.target_attribute
    }

@router.post("/identities/{mapping_id}/sync")
async def sync_identity_attributes(
    mapping_id: str,
    attributes: Dict,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Synchronize identity attributes.
    
    Args:
        mapping_id: Mapping ID
        attributes: New attributes
        service: Federation service
        
    Returns:
        Dict: Updated attributes
    """
    updated_attrs = await service.sync_attributes(mapping_id, attributes)
    return {"attributes": updated_attrs} 