"""Rule validator module."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RuleContext:
    """Context for rule validation."""

    code: str
    file_path: str
    metadata: Dict[str, Any]


class RuleValidator:
    """Validates code against rules."""

    def __init__(self, rules: List[Any] = None):
        """Initialize rule validator.

        Args:
            rules: List of validation rules
        """
        self.rules = rules or []

    def validate(self, context: RuleContext) -> List[str]:
        """Run rule validation.

        Args:
            context: Rule validation context

        Returns:
            List[str]: List of validation issues
        """
        issues = []
        for rule in self.rules:
            rule_issues = rule.validate(context)
            issues.extend(rule_issues)
        return issues


def create_default_validator() -> RuleValidator:
    """Create default rule validator.

    Returns:
        RuleValidator: Default rule validator
    """
    return RuleValidator()  # Add default rules here
