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

router = APIRouter(prefix="/federation", tags=["federation"])

async def get_federation_service(
    db: AsyncSession = Depends(get_session)
) -> FederationService:
    """Get federation service instance."""
    service = FederationService(db)
    await service.initialize()
    return service

@router.post("/identities")
async def link_federated_identity(
    user_id: str,
    identity: FederatedIdentityCreate,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Link federated identity to user.
    
    Args:
        user_id: User ID
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
    
    success = await service.link_identity(user_id, federated_identity)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity already linked"
        )
    
    return {"status": "success"}

@router.delete("/identities/{provider_id}")
async def unlink_federated_identity(
    user_id: str,
    provider_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Unlink federated identity from user.
    
    Args:
        user_id: User ID
        provider_id: Provider ID
        service: Federation service
        
    Returns:
        Dict: Success response
    """
    success = await service.unlink_identity(user_id, provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not found"
        )
    
    return {"status": "success"}

@router.put("/identities/{provider_id}/attributes")
async def sync_identity_attributes(
    user_id: str,
    provider_id: str,
    attributes: Dict,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Synchronize identity attributes.
    
    Args:
        user_id: User ID
        provider_id: Provider ID
        attributes: New attributes
        service: Federation service
        
    Returns:
        Dict: Updated attributes
    """
    updated_attrs = await service.sync_attributes(
        user_id,
        provider_id,
        attributes
    )
    
    return {"attributes": updated_attrs}

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

@router.delete("/trust/{provider_id}/{trusted_provider_id}")
async def revoke_trust_relationship(
    provider_id: str,
    trusted_provider_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Revoke trust relationship.
    
    Args:
        provider_id: Provider ID
        trusted_provider_id: Trusted provider ID
        service: Federation service
        
    Returns:
        Dict: Success response
    """
    success = await service.revoke_trust(provider_id, trusted_provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trust relationship not found"
        )
    
    return {"status": "success"}

@router.get("/trust/validate")
async def validate_trust_relationship(
    source_id: str,
    target_id: str,
    service: FederationService = Depends(get_federation_service)
) -> Dict:
    """Validate trust between providers.
    
    Args:
        source_id: Source provider ID
        target_id: Target provider ID
        service: Federation service
        
    Returns:
        Dict: Trust status
    """
    is_trusted = await service.validate_trust(source_id, target_id)
    return {"trusted": is_trusted}

@router.post("/attributes/mapping")
async def create_attribute_mapping(
    mapping: AttributeMappingCreate,
    db: AsyncSession = Depends(get_session)
) -> Dict:
    """Create attribute mapping.
    
    Args:
        mapping: Attribute mapping data
        db: Database session
        
    Returns:
        Dict: Created mapping
    """
    attr_mapping = AttributeMapping(
        provider_id=mapping.provider_id,
        source_attribute=mapping.source_attribute,
        target_attribute=mapping.target_attribute,
        transform_function=mapping.transform_function,
        is_required=mapping.is_required
    )
    
    db.add(attr_mapping)
    await db.commit()
    
    return {
        "id": str(attr_mapping.id),
        "provider_id": str(attr_mapping.provider_id),
        "source_attribute": attr_mapping.source_attribute,
        "target_attribute": attr_mapping.target_attribute
    } 