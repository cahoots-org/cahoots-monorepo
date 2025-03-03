"""Policy chain validation module."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ValidationContext:
    """Context for validation."""

    code: str
    file_path: str
    language: str
    metadata: Dict[str, Any]


class ValidationChain:
    """Chain of validation policies."""

    def __init__(self, policies: List[Any] = None):
        """Initialize validation chain.

        Args:
            policies: List of validation policies
        """
        self.policies = policies or []

    def validate(self, context: ValidationContext) -> List[str]:
        """Run validation chain.

        Args:
            context: Validation context

        Returns:
            List[str]: List of validation issues
        """
        issues = []
        for policy in self.policies:
            policy_issues = policy.validate(context)
            issues.extend(policy_issues)
        return issues

    @classmethod
    def create_default_chain(cls) -> "ValidationChain":
        """Create default validation chain.

        Returns:
            ValidationChain: Default validation chain
        """
        return cls(policies=[])  # Add default policies here
