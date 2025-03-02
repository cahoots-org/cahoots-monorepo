"""Version vector for optimistic concurrency control."""

from dataclasses import dataclass
from typing import Dict, Optional

from ..models.version_vector import VersionVectorProvider


@dataclass
class VersionVector:
    """Version vector for tracking event versions across branches."""

    versions: Dict[str, int]

    @classmethod
    def new(cls) -> "VersionVector":
        """Create a new empty version vector."""
        return cls(versions={"master": 0})

    @classmethod
    def from_provider(cls, provider: VersionVectorProvider) -> "VersionVector":
        """Create version vector from a provider."""
        if not provider.version_vector:
            return cls.new()
        return cls(versions=provider.version_vector)

    def compatible_with(self, other: "VersionVector") -> bool:
        """Check if this vector is compatible with another vector.

        Two vectors are compatible if they have the same branches and
        the other vector's versions are greater than or equal to this vector's.
        """
        if not other:
            return True

        for branch, version in self.versions.items():
            if branch not in other.versions:
                return False
            if other.versions[branch] < version:
                return False
        return True

    def increment(self, branch: str = "master") -> None:
        """Increment version for a branch."""
        if branch not in self.versions:
            self.versions[branch] = 0
        self.versions[branch] += 1

    def merge(self, other: "VersionVector") -> None:
        """Merge another vector into this one.

        Takes the maximum version for each branch.
        """
        for branch, version in other.versions.items():
            if branch not in self.versions or self.versions[branch] < version:
                self.versions[branch] = version
