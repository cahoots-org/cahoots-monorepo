"""Base exceptions for the events system."""
# Use absolute import based on project structure
from libs.core.cahoots_core.exceptions import CahootsError, ErrorCategory, ErrorSeverity

# Re-export for convenience
__all__ = ["CahootsError", "ErrorCategory", "ErrorSeverity"]