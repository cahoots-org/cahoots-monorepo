"""Base exceptions for the events system."""
from cahoots_core.exceptions import CahootsError, ErrorCategory, ErrorSeverity

# Re-export for convenience
__all__ = ["CahootsError", "ErrorCategory", "ErrorSeverity"] 