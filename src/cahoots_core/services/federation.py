"""Federation service."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, update, insert

from cahoots_core.models.federation import (
    FederatedIdentity,
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)
from cahoots_core.validation.trust_chain import TrustChainValidator

class FederationService:
    """Federation service."""

    def __init__(self, db, trust_chain: TrustChainValidator):
        """Initialize federation service.

        Args:
            db: Database client
            trust_chain: Trust chain validator
        """
        self.db = db
        self.trust_chain = trust_chain

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
        mapping_id: str
    ) -> Optional[FederatedIdentity]:
        """Get federated identity by mapping ID.

        Args:
            mapping_id: Mapping ID

        Returns:
            Optional[FederatedIdentity]: Federated identity if found
        """
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.id == mapping_id,
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
        # Check if identity already exists
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.external_id == identity.external_id,
            FederatedIdentityMapping.provider_id == identity.provider_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return False

        # Create new mapping
        mapping = FederatedIdentityMapping(
            user_id=user_id,
            external_id=identity.external_id,
            provider_id=identity.provider_id,
            attributes=identity.attributes,
            metadata=identity.metadata,
            is_active=True
        )
        await self.db.execute(insert(FederatedIdentityMapping).values(mapping.__dict__))
        await self.db.commit()
        return True

    async def unlink_identity(
        self,
        mapping_id: str
    ) -> bool:
        """Unlink federated identity.

        Args:
            mapping_id: Mapping ID

        Returns:
            bool: Success status
        """
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.id == mapping_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            stmt = update(FederatedIdentityMapping).where(
                FederatedIdentityMapping.id == mapping_id
            ).values(is_active=False)
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        return False

    async def sync_attributes(
        self,
        mapping_id: str,
        attributes: Dict
    ) -> Dict:
        """Synchronize identity attributes.

        Args:
            mapping_id: Mapping ID
            attributes: New attributes

        Returns:
            Dict: Updated attributes
        """
        # Get identity mapping
        stmt = select(FederatedIdentityMapping).where(
            FederatedIdentityMapping.id == mapping_id,
            FederatedIdentityMapping.is_active == True
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if not mapping:
            return {}

        # Get attribute mappings for provider
        stmt = select(AttributeMapping).where(
            AttributeMapping.provider_id == mapping.provider_id
        )
        result = await self.db.execute(stmt)
        attr_mappings = result.scalars().all()

        # Apply attribute mappings
        updated_attrs = mapping.attributes.copy()
        for attr_map in attr_mappings:
            if attr_map.source_attribute in attributes:
                value = attributes[attr_map.source_attribute]
                if attr_map.transform_function:
                    value = attr_map.transform_function(value)
                updated_attrs.setdefault(attr_map.target_attribute, value)

        # Update mapping attributes
        stmt = update(FederatedIdentityMapping).where(
            FederatedIdentityMapping.id == mapping_id
        ).values(attributes=updated_attrs)
        await self.db.execute(stmt)
        await self.db.commit()

        return updated_attrs

    async def establish_trust(
        self,
        provider_id: str,
        trusted_provider_id: str,
        trust_level: str = "direct",
        valid_until: Optional[datetime] = None
    ) -> Optional[TrustRelationship]:
        """Establish trust relationship.

        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
            trust_level: Trust level
            valid_until: Valid until date

        Returns:
            Optional[TrustRelationship]: Trust relationship if created
        """
        relationship = TrustRelationship(
            provider_id=provider_id,
            trusted_provider_id=trusted_provider_id,
            trust_level=trust_level,
            valid_until=valid_until or datetime.utcnow() + timedelta(days=365),
            is_active=True
        )
        await self.db.execute(insert(TrustRelationship).values(relationship.__dict__))
        await self.db.commit()

        self.trust_chain.add_trust(
            str(provider_id),
            str(trusted_provider_id)
        )

        return relationship

    async def revoke_trust(
        self,
        relationship_id: str
    ) -> bool:
        """Revoke trust relationship.

        Args:
            relationship_id: Relationship ID

        Returns:
            bool: Success status
        """
        stmt = select(TrustRelationship).where(
            TrustRelationship.id == relationship_id,
            TrustRelationship.is_active == True
        )
        result = await self.db.execute(stmt)
        relationship = result.scalar_one_or_none()

        if relationship:
            stmt = update(TrustRelationship).where(
                TrustRelationship.id == relationship_id
            ).values(is_active=False)
            await self.db.execute(stmt)
            await self.db.commit()

            # Remove from trust chain
            self.trust_chain.remove_trust(
                str(relationship.provider_id),
                str(relationship.trusted_provider_id)
            )
            return True
        return False

    async def validate_trust(
        self,
        provider_id: str,
        trusted_provider_id: str
    ) -> bool:
        """Validate trust relationship.

        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID

        Returns:
            bool: Trust status
        """
        return self.trust_chain.validate_chain(provider_id, trusted_provider_id) 