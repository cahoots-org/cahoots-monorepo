"""Trust chain validation module."""
from typing import Dict, List, Set

class TrustChainValidator:
    """Validates trust relationships between providers."""
    
    def __init__(self):
        """Initialize trust chain validator."""
        self.trust_graph: Dict[str, Set[str]] = {}
        
    def add_trust(self, provider_id: str, trusted_provider_id: str) -> None:
        """Add trust relationship to graph.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
        """
        if provider_id not in self.trust_graph:
            self.trust_graph[provider_id] = set()
        self.trust_graph[provider_id].add(trusted_provider_id)
        
    def remove_trust(self, provider_id: str, trusted_provider_id: str) -> None:
        """Remove trust relationship from graph.
        
        Args:
            provider_id: Provider ID
            trusted_provider_id: Trusted provider ID
        """
        if provider_id in self.trust_graph:
            self.trust_graph[provider_id].discard(trusted_provider_id)
            
    def validate_chain(self, provider_id: str, target_provider_id: str) -> bool:
        """Validate trust chain between providers.
        
        Args:
            provider_id: Provider ID
            target_provider_id: Target provider ID
            
        Returns:
            bool: Whether trust exists
        """
        if provider_id not in self.trust_graph:
            return False
            
        # Direct trust
        if target_provider_id in self.trust_graph[provider_id]:
            return True
            
        # Transitive trust (depth-first search)
        visited = {provider_id}
        stack = list(self.trust_graph[provider_id])
        
        while stack:
            current = stack.pop()
            if current == target_provider_id:
                return True
                
            if current not in visited and current in self.trust_graph:
                visited.add(current)
                stack.extend(p for p in self.trust_graph[current] if p not in visited)
                
        return False 