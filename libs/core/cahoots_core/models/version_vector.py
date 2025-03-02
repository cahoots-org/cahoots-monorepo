"""Version vector interface for optimistic concurrency control."""

from typing import Dict, Protocol


class VersionVectorProvider(Protocol):
    """Protocol for objects that provide version vectors."""

    @property
    def version_vector(self) -> Dict[str, int]:
        """Get the version vector."""
        ...
