"""Version vector implementation for conflict detection and resolution."""
from typing import Dict, Optional, List
from datetime import datetime
import json

from src.database.models import ContextEvent

class VersionVector:
    """Version vector for tracking causal relationships between events."""
    
    def __init__(self, versions: Optional[Dict[str, int]] = None):
        """Initialize version vector.
        
        Args:
            versions: Optional initial version mapping
        """
        self.versions = versions or {}
        self.timestamp = datetime.utcnow()
        
    @classmethod
    def new(cls) -> 'VersionVector':
        """Create a new empty version vector."""
        return cls()
        
    @classmethod
    def from_json(cls, json_str: str) -> 'VersionVector':
        """Create version vector from JSON string.
        
        Args:
            json_str: JSON string containing version data
            
        Returns:
            VersionVector instance
        """
        data = json.loads(json_str)
        vector = cls(versions=data.get("versions", {}))
        if "timestamp" in data:
            vector.timestamp = datetime.fromisoformat(data["timestamp"])
        return vector
        
    @classmethod
    def from_event(cls, event: ContextEvent) -> 'VersionVector':
        """Create version vector from event data.
        
        Args:
            event: Context event containing version data
            
        Returns:
            VersionVector instance
        """
        if not event.version_vector:
            return cls()
            
        # Handle JSON string version vector
        if isinstance(event.version_vector, str):
            return cls.from_json(event.version_vector)
            
        vector = cls(versions=event.version_vector)
        if hasattr(event, 'timestamp'):
            vector.timestamp = event.timestamp
        return vector
            
    def increment(self, node_id: str) -> None:
        """Increment version for a node.
        
        Args:
            node_id: ID of node to increment
        """
        self.versions[node_id] = self.versions.get(node_id, 0) + 1
        self.timestamp = datetime.utcnow()
        
    def merge(self, other: 'VersionVector') -> 'VersionVector':
        """Merge with another version vector.
        
        Args:
            other: Version vector to merge with
            
        Returns:
            New merged version vector
        """
        merged = {}
        all_nodes = set(self.versions.keys()) | set(other.versions.keys())
        
        for node in all_nodes:
            merged[node] = max(
                self.versions.get(node, 0),
                other.versions.get(node, 0)
            )
            
        result = VersionVector(merged)
        result.timestamp = max(self.timestamp, other.timestamp)
        return result
        
    def compatible_with(self, other: 'VersionVector') -> bool:
        """Check if this vector is causally compatible with another.
        
        Args:
            other: Version vector to compare with
            
        Returns:
            True if vectors are causally compatible
        """
        # Check if either vector is strictly newer
        if self.dominates(other) or other.dominates(self):
            return True
            
        # Check for concurrent modifications
        return not self.concurrent_with(other)
        
    def dominates(self, other: 'VersionVector') -> bool:
        """Check if this vector dominates (is newer than) another.
        
        Args:
            other: Version vector to compare with
            
        Returns:
            True if this vector dominates the other
        """
        at_least_one_greater = False
        for node, version in self.versions.items():
            other_version = other.versions.get(node, 0)
            if version < other_version:
                return False
            if version > other_version:
                at_least_one_greater = True
                
        # Check nodes only in other vector
        for node in other.versions:
            if node not in self.versions and other.versions[node] > 0:
                return False
                
        return at_least_one_greater
        
    def concurrent_with(self, other: 'VersionVector') -> bool:
        """Check if this vector represents concurrent modifications with another.
        
        Args:
            other: Version vector to compare with
            
        Returns:
            True if vectors represent concurrent modifications
        """
        all_nodes = set(self.versions.keys()) | set(other.versions.keys())
        
        found_greater = False
        found_less = False
        
        for node in all_nodes:
            self_version = self.versions.get(node, 0)
            other_version = other.versions.get(node, 0)
            
            if self_version > other_version:
                found_greater = True
            if self_version < other_version:
                found_less = True
                
            if found_greater and found_less:
                return True
                
        return False
        
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation.
        
        Returns:
            Dict containing version data
        """
        return self.versions
        
    def to_json(self) -> str:
        """Convert to JSON string representation.
        
        Returns:
            JSON string containing version data
        """
        return json.dumps({
            "versions": self.versions,
            "timestamp": self.timestamp.isoformat()
        })
        
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionVector):
            return NotImplemented
        return self.versions == other.versions
        
    def __str__(self) -> str:
        return f"VersionVector({self.versions})"
        
    def __repr__(self) -> str:
        return self.__str__() 