"""Base federation provider interface."""
from typing import Dict, List, Optional, Protocol
from datetime import datetime
from abc import ABC, abstractmethod
import uuid

class FederatedIdentity:
    """Federated identity information."""
    
    def __init__(
        self,
        external_id: str,
        provider_id: str,
        attributes: Dict,
        metadata: Optional[Dict] = None
    ):
        """Initialize federated identity.
        
        Args:
            external_id: External identifier
            provider_id: Federation provider ID
            attributes: Identity attributes
            metadata: Additional metadata
        """
        self.id = str(uuid.uuid4())
        self.external_id = external_id
        self.provider_id = provider_id
        self.attributes = attributes
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'external_id': self.external_id,
            'provider_id': self.provider_id,
            'attributes': self.attributes,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class FederationProvider(ABC):
    """Base federation provider interface."""
    
    @abstractmethod
    async def get_identity(self, external_id: str) -> Optional[FederatedIdentity]:
        """Get federated identity by external ID.
        
        Args:
            external_id: External identifier
            
        Returns:
            Optional[FederatedIdentity]: Federated identity if found
        """
        pass
    
    @abstractmethod
    async def link_identity(self, user_id: str, identity: FederatedIdentity) -> bool:
        """Link federated identity to local user.
        
        Args:
            user_id: Local user ID
            identity: Federated identity
            
        Returns:
            bool: Success status
        """
        pass
    
    @abstractmethod
    async def unlink_identity(self, user_id: str, external_id: str) -> bool:
        """Unlink federated identity from local user.
        
        Args:
            user_id: Local user ID
            external_id: External identifier
            
        Returns:
            bool: Success status
        """
        pass
    
    @abstractmethod
    async def sync_attributes(self, identity: FederatedIdentity) -> Dict:
        """Synchronize identity attributes.
        
        Args:
            identity: Federated identity
            
        Returns:
            Dict: Updated attributes
        """
        pass
    
    @abstractmethod
    async def validate_trust(self, provider_id: str) -> bool:
        """Validate trust relationship with provider.
        
        Args:
            provider_id: Provider ID to validate
            
        Returns:
            bool: Trust status
        """
        pass

class AttributeMapper(Protocol):
    """Protocol for attribute mapping."""
    
    def map_attributes(self, source_attrs: Dict, mapping: Dict[str, str]) -> Dict:
        """Map attributes according to configuration.
        
        Args:
            source_attrs: Source attributes
            mapping: Attribute mapping configuration
            
        Returns:
            Dict: Mapped attributes
        """
        mapped = {}
        for target_key, source_key in mapping.items():
            if source_key in source_attrs:
                mapped[target_key] = source_attrs[source_key]
        return mapped

class TrustChain:
    """Federation trust chain management."""
    
    def __init__(self, max_depth: int = 3):
        """Initialize trust chain.
        
        Args:
            max_depth: Maximum chain depth
        """
        self.max_depth = max_depth
        self._trust_relationships: Dict[str, List[str]] = {}
    
    def add_trust(self, provider_id: str, trusted_provider_id: str) -> None:
        """Add trust relationship.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
        """
        if provider_id not in self._trust_relationships:
            self._trust_relationships[provider_id] = []
        if trusted_provider_id not in self._trust_relationships[provider_id]:
            self._trust_relationships[provider_id].append(trusted_provider_id)
    
    def remove_trust(self, provider_id: str, trusted_provider_id: str) -> None:
        """Remove trust relationship.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
        """
        if provider_id in self._trust_relationships:
            self._trust_relationships[provider_id].remove(trusted_provider_id)
    
    def validate_chain(self, source_id: str, target_id: str, depth: int = 0) -> bool:
        """Validate trust chain between providers.
        
        Args:
            source_id: Source provider ID
            target_id: Target provider ID
            depth: Current chain depth
            
        Returns:
            bool: Whether trust chain is valid
        """
        # Check depth before doing anything else
        if depth >= self.max_depth:
            return False
            
        if source_id not in self._trust_relationships:
            return False
            
        trusted_providers = self._trust_relationships[source_id]
        
        # Direct trust
        if target_id in trusted_providers:
            return True
            
        # Transitive trust
        for trusted_id in trusted_providers:
            if self.validate_chain(trusted_id, target_id, depth + 1):
                return True
                
        return False 