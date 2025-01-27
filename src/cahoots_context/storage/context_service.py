import json
from typing import Dict
from cahoots_core.exceptions import CahootsError
from cahoots_core.exceptions.base import ErrorCategory, ErrorSeverity, ContextLimitError

class ContextService:
    def _check_memory_limit(self, data: Dict) -> None:
        """Check if data exceeds memory limits."""
        size = len(json.dumps(data))
        if size > self.MAX_SIZE_BYTES:
            raise ContextLimitError(
                message=f"Data size {size} exceeds limit {self.MAX_SIZE_BYTES}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.RESOURCE_LIMIT
            )

    async def apply_architectural_decision(self, context: Dict, event_data: Dict) -> None:
        """Apply architectural decision event to context."""
        if len(context.get("architectural_decisions", [])) >= self.MAX_ITEMS:
            raise ContextLimitError(
                message=f"Architectural decisions exceed limit {self.MAX_ITEMS}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.RESOURCE_LIMIT
            ) 