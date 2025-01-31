from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

class PatternLibrary:
    """Manages and applies UI design patterns."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns = self._load_base_patterns()
        
    def _load_base_patterns(self) -> Dict[str, Any]:
        """Load base UI patterns."""
        return {
            "navigation": {
                "horizontal": {
                    "description": "Horizontal navigation bar",
                    "accessibility": {
                        "role": "navigation",
                        "aria-label": "Main navigation"
                    },
                    "responsive": {
                        "mobile": "hamburger",
                        "tablet": "horizontal",
                        "desktop": "horizontal"
                    }
                },
                "vertical": {
                    "description": "Vertical navigation menu",
                    "accessibility": {
                        "role": "navigation",
                        "aria-label": "Side navigation"
                    }
                }
            },
            "forms": {
                "stacked": {
                    "description": "Vertically stacked form layout",
                    "accessibility": {
                        "role": "form",
                        "aria-label": "Form section"
                    }
                },
                "inline": {
                    "description": "Horizontal inline form layout",
                    "accessibility": {
                        "role": "form",
                        "aria-label": "Inline form"
                    }
                }
            },
            "cards": {
                "basic": {
                    "description": "Basic content card",
                    "accessibility": {
                        "role": "article"
                    }
                },
                "interactive": {
                    "description": "Clickable card with hover states",
                    "accessibility": {
                        "role": "button",
                        "tabindex": "0"
                    }
                }
            }
        }
    
    async def select_patterns(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate patterns based on requirements.
        
        Args:
            requirements: Design requirements and constraints
            
        Returns:
            Dict containing selected patterns and their configurations
        """
        try:
            selected = {}
            
            # Analyze requirements
            needs_navigation = self._check_navigation_requirements(requirements)
            needs_forms = self._check_form_requirements(requirements)
            needs_cards = self._check_card_requirements(requirements)
            
            # Select navigation patterns
            if needs_navigation:
                selected["navigation"] = self._select_navigation_pattern(requirements)
            
            # Select form patterns
            if needs_forms:
                selected["forms"] = self._select_form_pattern(requirements)
            
            # Select card patterns
            if needs_cards:
                selected["cards"] = self._select_card_pattern(requirements)
            
            return {
                "patterns": selected,
                "metadata": {
                    "selected_at": datetime.now().isoformat(),
                    "requirements_hash": hash(str(requirements))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Pattern selection failed: {str(e)}")
            return {
                "patterns": {},
                "error": str(e),
                "metadata": {
                    "error_at": datetime.now().isoformat()
                }
            }
    
    def _check_navigation_requirements(self, requirements: Dict[str, Any]) -> bool:
        """Check if navigation patterns are needed."""
        keywords = {"navigation", "menu", "nav", "header", "sidebar"}
        return any(keyword in str(requirements).lower() for keyword in keywords)
    
    def _check_form_requirements(self, requirements: Dict[str, Any]) -> bool:
        """Check if form patterns are needed."""
        keywords = {"form", "input", "submit", "field", "validation"}
        return any(keyword in str(requirements).lower() for keyword in keywords)
    
    def _check_card_requirements(self, requirements: Dict[str, Any]) -> bool:
        """Check if card patterns are needed."""
        keywords = {"card", "tile", "grid", "collection", "list"}
        return any(keyword in str(requirements).lower() for keyword in keywords)
    
    def _select_navigation_pattern(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate navigation pattern."""
        is_mobile_first = requirements.get("mobile_first", False)
        is_vertical = requirements.get("vertical_layout", False)
        
        if is_vertical:
            return self.patterns["navigation"]["vertical"]
        else:
            pattern = self.patterns["navigation"]["horizontal"]
            if is_mobile_first:
                pattern["responsive"]["default"] = "hamburger"
            return pattern
    
    def _select_form_pattern(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate form pattern."""
        is_compact = requirements.get("compact", False)
        has_many_fields = requirements.get("field_count", 0) > 3
        
        if is_compact and not has_many_fields:
            return self.patterns["forms"]["inline"]
        else:
            return self.patterns["forms"]["stacked"]
    
    def _select_card_pattern(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate card pattern."""
        is_interactive = requirements.get("interactive", False)
        
        if is_interactive:
            return self.patterns["cards"]["interactive"]
        else:
            return self.patterns["cards"]["basic"] 