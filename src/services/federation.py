"""Federation service."""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.federation.base import FederatedIdentity, TrustChain
from src.models.federation import (
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)
from src.models.identity_provider import IdentityProvider
from src.models.user import User

class FederationService:
    """Service for managing federated identities."""
    
    def __init__(self, db: AsyncSession):
        """Initialize federation service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.trust_chain = TrustChain()
        
    async def initialize(self) -> None:
        """Initialize federation service.
        
        Loads trust relationships into memory.
        """
        # Load active trust relationships
        stmt = select(TrustRelationship).where(
            TrustRelationship.is_active == True,
            TrustRelationship.valid_until > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        relationships = result.scalars().all()
        
        # Build trust chain
        for rel in relationships:
            self.trust_chain.add_trust(
                str(rel.provider_id),
                str(rel.trusted_provider_id)
            )

    async def get_federated_identity(
        self,
        user_id: str,
        provider_id: str
    ) -> Optional[FederatedIdentity]:
        """Get federated identity for user and provider.
        
        Args:
            user_id: User ID
            provider_id: Provider ID
            
        Returns:
            Optional[FederatedIdentity]: Federated identity if found
        """
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.user_id == user_id,
            FederatedIdentityMapping.provider_id == provider_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            return FederatedIdentity(
                external_id=mapping.external_id,
                provider_id=str(mapping.provider_id),
                attributes=mapping.attributes,
                metadata=mapping.metadata
            )
        return None

    async def link_identity(
        self,
        user_id: str,
        identity: FederatedIdentity
    ) -> bool:
        """Link federated identity to user.
        
        Args:
            user_id: User ID
            identity: Federated identity
            
        Returns:
            bool: Success status
        """
        # Check if mapping already exists
        existing = await self.get_federated_identity(
            user_id,
            identity.provider_id
        )
        if existing:
            return False
            
        # Create new mapping
        mapping = FederatedIdentityMapping(
            user_id=user_id,
            provider_id=identity.provider_id,
            external_id=identity.external_id,
            attributes=identity.attributes,
            metadata=identity.metadata
        )
        self.db.add(mapping)
        await self.db.commit()
        
        return True

    async def unlink_identity(
        self,
        user_id: str,
        provider_id: str
    ) -> bool:
        """Unlink federated identity from user.
        
        Args:
            user_id: User ID
            provider_id: Provider ID
            
        Returns:
            bool: Success status
        """
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.user_id == user_id,
            FederatedIdentityMapping.provider_id == provider_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            mapping.is_active = False
            await self.db.commit()
            return True
            
        return False

    async def sync_attributes(
        self,
        user_id: str,
        provider_id: str,
        attributes: Dict
    ) -> Dict:
        """Synchronize identity attributes.
        
        Args:
            user_id: User ID
            provider_id: Provider ID
            attributes: New attributes
            
        Returns:
            Dict: Updated attributes
        """
        # Get attribute mappings for provider
        stmt = select(AttributeMapping).where(
            AttributeMapping.provider_id == provider_id
        )
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()
        
        # Apply mappings
        mapped_attrs = {}
        for mapping in mappings:
            if mapping.source_attribute in attributes:
                value = attributes[mapping.source_attribute]
                
                # Apply transformation if specified
                if mapping.transform_function:
                    # TODO: Implement attribute transformation
                    pass
                    
                mapped_attrs[mapping.target_attribute] = value
        
        # Update identity mapping
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.user_id == user_id,
            FederatedIdentityMapping.provider_id == provider_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            mapping.attributes.update(mapped_attrs)
            mapping.last_synced = datetime.utcnow()
            await self.db.commit()
            
        return mapped_attrs

    async def establish_trust(
        self,
        provider_id: str,
        trusted_provider_id: str,
        trust_level: str = "direct",
        valid_days: int = 365,
        metadata: Optional[Dict] = None
    ) -> TrustRelationship:
        """Establish trust relationship between providers.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
            trust_level: Trust level (direct/transitive)
            valid_days: Validity period in days
            metadata: Additional metadata
            
        Returns:
            TrustRelationship: Created relationship
        """
        # Create trust relationship
        relationship = TrustRelationship(
            provider_id=provider_id,
            trusted_provider_id=trusted_provider_id,
            trust_level=trust_level,
            metadata=metadata or {},
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=valid_days)
        )
        self.db.add(relationship)
        await self.db.commit()
        
        # Update trust chain
        self.trust_chain.add_trust(
            str(provider_id),
            str(trusted_provider_id)
        )
        
        return relationship

    async def revoke_trust(
        self,
        provider_id: str,
        trusted_provider_id: str
    ) -> bool:
        """Revoke trust relationship.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
            
        Returns:
            bool: Success status
        """
        stmt = select(TrustRelationship).where(
            TrustRelationship.provider_id == provider_id,
            TrustRelationship.trusted_provider_id == trusted_provider_id,
            TrustRelationship.is_active == True
        )
        result = await self.db.execute(stmt)
        relationship = result.scalar_one_or_none()
        
        if relationship:
            relationship.is_active = False
            relationship.valid_until = datetime.utcnow()
            await self.db.commit()
            
            # Update trust chain
            self.trust_chain.remove_trust(
                str(provider_id),
                str(trusted_provider_id)
            )
            
            return True
            
        return False

    async def validate_trust(
        self,
        source_id: str,
        target_id: str
    ) -> bool:
        """Validate trust between providers.
        
        Args:
            source_id: Source provider ID
            target_id: Target provider ID
            
        Returns:
            bool: Trust status
        """
        return self.trust_chain.validate_chain(source_id, target_id) 