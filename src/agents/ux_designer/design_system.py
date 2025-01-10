"""Design system module for UX Designer agent."""
from typing import Dict, Any, List, Optional, Union
import logging
import re
import colorsys
import warnings
from datetime import datetime

class DesignSystem:
    """AI-powered design system that generates and manages design patterns."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize design system with configuration.
        
        Args:
            config: Configuration dictionary containing design system settings
        """
        self.logger = logging.getLogger(__name__)
        self.version = config.get('version', '1.0')
        self.model = config.get('model', 'gpt-4-1106-preview')
        self.brand_context = config.get('brand_context', {})
        self.base_font_size = 16  # Default browser font size in pixels
        self.cached_tokens = {}  # Cache for generated tokens
        
    def _format_rem(self, px_value: float) -> str:
        """Format a pixel value as a rem value.
        
        Args:
            px_value: Value in pixels
            
        Returns:
            Formatted rem value
        """
        rem = px_value / self.base_font_size
        # Format with up to 3 decimal places, removing trailing zeros and decimal point
        formatted = f"{rem:.3f}".rstrip('0').rstrip('.')
        return f"{formatted}rem"
        
    def _convert_to_px(self, value: str) -> Optional[float]:
        """Convert a CSS value to pixels.
        
        Args:
            value: CSS value to convert
            
        Returns:
            Value in pixels or None if conversion fails
        """
        if not isinstance(value, str):
            return None
            
        # Handle rem values
        if value.endswith('rem'):
            try:
                rem = float(value[:-3])
                return rem * self.base_font_size
            except ValueError:
                return None
                
        # Handle px values
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError:
                return None
                
        # Handle em values (treat same as rem)
        if value.endswith('em'):
            try:
                em = float(value[:-2])
                return em * self.base_font_size
            except ValueError:
                return None
                
        return None

    def _hsl_to_rgb(self, h: float, s: float, l: float) -> tuple[int, int, int]:
        """Convert HSL color values to RGB.
        
        Args:
            h: Hue angle in degrees [0, 360]
            s: Saturation percentage [0, 100]
            l: Lightness percentage [0, 100]
            
        Returns:
            Tuple of (r, g, b) values in range [0, 255]
        """
        # Convert to [0, 1] range
        h = (h % 360) / 360
        s = s / 100
        l = l / 100
        
        if s == 0:
            # Achromatic (gray)
            rgb = l, l, l
        else:
            def hue_to_rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)
            rgb = r, g, b
            
        # Convert to 8-bit RGB values
        return tuple(round(c * 255) for c in rgb)

    def _normalize_colors(self, colors: Dict[str, str]) -> Dict[str, str]:
        """Normalize color values to consistent format.
        
        Args:
            colors: Dictionary of color values
            
        Returns:
            Normalized color values
        """
        normalized = {}
        for key, value in colors.items():
            # Handle None values
            if value is None:
                normalized[key] = value
                continue
                
            # Handle non-string values
            if not isinstance(value, str):
                normalized[key] = value
                continue
                
            # Handle empty strings
            if not value:
                normalized[key] = value
                continue
                
            # Preserve CSS variables and keywords
            if value.startswith('var(') or value in ['currentColor', 'transparent', 'inherit']:
                normalized[key] = value
                continue
                
            try:
                # Handle shorthand hex
                if re.match(r'^#[0-9a-fA-F]{3}$', value):
                    expanded = ''.join(c + c for c in value[1:])
                    normalized[key] = f"#{expanded.lower()}"
                    continue
                    
                # Handle full hex
                if re.match(r'^#[0-9a-fA-F]{6}$', value):
                    normalized[key] = value.lower()
                    continue
                    
                # Handle hex with alpha
                if re.match(r'^#[0-9a-fA-F]{8}$', value):
                    normalized[key] = value.lower()
                    continue
                    
                # Handle rgb/rgba
                rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)', value)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups()[:3])
                    a = rgb_match.group(4)
                    
                    # If RGB values are out of range, preserve original
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        normalized[key] = value
                        continue
                        
                    if a is not None:
                        try:
                            a = round(float(a) * 255)
                            a = max(0, min(255, a))
                            normalized[key] = f"#{r:02x}{g:02x}{b:02x}{a:02x}".lower()
                        except ValueError:
                            normalized[key] = value
                    else:
                        normalized[key] = f"#{r:02x}{g:02x}{b:02x}".lower()
                    continue
                    
                # Handle hsl/hsla
                hsl_match = re.match(r'hsla?\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%(?:\s*,\s*([\d.]+))?\s*\)', value)
                if hsl_match:
                    h, s, l = map(float, hsl_match.groups()[:3])
                    a = hsl_match.group(4)
                    
                    # If HSL values are out of range, preserve original
                    if not (0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100):
                        normalized[key] = value
                        continue
                        
                    # Convert HSL to RGB using our custom conversion
                    r, g, b = self._hsl_to_rgb(h, s, l)
                    
                    if a is not None:
                        try:
                            # Convert alpha to 8-bit value (0-255)
                            a = int(float(a) * 255)  # Truncate decimal instead of rounding
                            a = max(0, min(255, a))  # Clamp to valid range
                            normalized[key] = f"#{r:02x}{g:02x}{b:02x}{a:02x}".lower()
                        except ValueError:
                            normalized[key] = value
                    else:
                        normalized[key] = f"#{r:02x}{g:02x}{b:02x}".lower()
                    continue
                    
            except (ValueError, AttributeError) as e:
                warnings.warn(f"Could not normalize color {value}, keeping original: {str(e)}")
                normalized[key] = value
                continue
                
            # Keep original if no patterns match
            normalized[key] = value
                
        return normalized

    def _normalize_typography(self, typography: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Normalize typography values.
        
        Args:
            typography: Typography configuration
            
        Returns:
            Normalized typography values
        """
        # Validate typography values first
        self._validate_typography(typography)
        
        normalized = {
            "fontFamilies": {},
            "fontSizes": {},
            "fontWeights": {},
            "lineHeights": {}
        }
        
        # Normalize font families
        for key, value in typography.get("fontFamilies", {}).items():
            if not isinstance(value, str):
                warnings.warn(f"Invalid font family value for '{key}'")
                normalized["fontFamilies"][key] = value
                continue
                
            # Clean up whitespace around commas
            normalized["fontFamilies"][key] = re.sub(r'\s*,\s*', ', ', value.strip())
            
        # Normalize font sizes
        for key, value in typography.get("fontSizes", {}).items():
            if not isinstance(value, str):
                warnings.warn(f"Invalid font size value for '{key}'")
                normalized["fontSizes"][key] = value
                continue
                
            px = self._convert_to_px(value)
            if px is not None:
                normalized["fontSizes"][key] = self._format_rem(px)
            else:
                warnings.warn(f"Invalid font size value for '{key}'")
                normalized["fontSizes"][key] = value
                
        # Normalize font weights
        weight_map = {
            "thin": 100,
            "extralight": 200,
            "light": 300,
            "regular": 400,
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
            "extrabold": 800,
            "black": 900
        }
        
        for key, value in typography.get("fontWeights", {}).items():
            if isinstance(value, (int, str)):
                if isinstance(value, str) and value.lower() in weight_map:
                    normalized["fontWeights"][key] = weight_map[value.lower()]
                else:
                    try:
                        weight = int(str(value))
                        if 100 <= weight <= 900 and weight % 100 == 0:
                            normalized["fontWeights"][key] = weight
                        else:
                            warnings.warn(f"Invalid font weight value for '{key}'")
                            normalized["fontWeights"][key] = value
                    except ValueError:
                        warnings.warn(f"Invalid font weight value for '{key}'")
                        normalized["fontWeights"][key] = value
            else:
                warnings.warn(f"Invalid font weight value for '{key}'")
                normalized["fontWeights"][key] = value
                
        # Normalize line heights
        for key, value in typography.get("lineHeights", {}).items():
            if isinstance(value, (int, float)):
                normalized["lineHeights"][key] = float(value)
            elif isinstance(value, str):
                if value.endswith('px'):
                    try:
                        px = float(value[:-2])
                        normalized["lineHeights"][key] = px / self.base_font_size
                    except ValueError:
                        warnings.warn(f"Invalid line height value for '{key}'")
                        normalized["lineHeights"][key] = value
                elif value.endswith('rem'):
                    try:
                        normalized["lineHeights"][key] = float(value[:-3])
                    except ValueError:
                        warnings.warn(f"Invalid line height value for '{key}'")
                        normalized["lineHeights"][key] = value
                elif value.endswith('em'):
                    try:
                        normalized["lineHeights"][key] = float(value[:-2])
                    except ValueError:
                        warnings.warn(f"Invalid line height value for '{key}'")
                        normalized["lineHeights"][key] = value
                else:
                    try:
                        normalized["lineHeights"][key] = float(value)
                    except ValueError:
                        warnings.warn(f"Invalid line height value for '{key}'")
                        normalized["lineHeights"][key] = value
            else:
                warnings.warn(f"Invalid line height value for '{key}'")
                normalized["lineHeights"][key] = value
                
        return normalized

    def _normalize_spacing(self, spacing: Dict[str, str]) -> Dict[str, str]:
        """Normalize spacing values.
        
        Args:
            spacing: Spacing configuration
            
        Returns:
            Normalized spacing values
        """
        normalized = {}
        for key, value in spacing.items():
            if not isinstance(value, str):
                warnings.warn(f"Invalid spacing value for '{key}'")
                normalized[key] = value
                continue
                
            # Handle calc() expressions and CSS variables
            if value.startswith(('calc(', 'var(')):
                normalized[key] = value
                continue
                
            # Handle negative values
            if value.startswith('-'):
                normalized[key] = '0rem'
                continue
                
            # Handle invalid mixed units (e.g. "16px + 1rem")
            if '+' in value or ' ' in value.strip():
                normalized[key] = '1rem'  # Fallback to base
                continue
                
            px = self._convert_to_px(value)
            if px is not None:
                normalized[key] = self._format_rem(px)
            else:
                normalized[key] = '1rem'  # Fallback to base
                
        return normalized

    def _normalize_styles(self, styles: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize style values.
        
        Args:
            styles: Style configuration
            
        Returns:
            Normalized style values
        """
        normalized = {}
        for key, value in styles.items():
            # Convert camelCase to kebab-case
            normalized_key = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', key).lower()
            
            # Handle color values
            if any(color_prop in normalized_key for color_prop in ['color', 'background', 'border', 'shadow']):
                if isinstance(value, str):
                    normalized[normalized_key] = next(iter(self._normalize_colors({'temp': value}).values()))
                else:
                    normalized[normalized_key] = value
                continue
                
            # Handle spacing and font size values
            if any(unit_prop in normalized_key for unit_prop in ['margin', 'padding', 'gap', 'spacing', 'font-size']):
                if isinstance(value, str):
                    px = self._convert_to_px(value)
                    if px is not None:
                        normalized[normalized_key] = self._format_rem(px)
                    else:
                        normalized[normalized_key] = value
                else:
                    normalized[normalized_key] = value
                continue
                
            normalized[normalized_key] = value
            
        return normalized

    def _normalize_variants(self, variants: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Normalize component variants.
        
        Args:
            variants: List of variants
            
        Returns:
            Normalized variants
        """
        self._validate_variant_priorities(variants)
        
        # Track used priorities to handle conflicts
        used_priorities = set()
        normalized = {}
        next_priority = 1
        
        # First pass: assign valid priorities
        for variant in variants:
            if isinstance(variant, str):
                while next_priority in used_priorities:
                    next_priority += 1
                used_priorities.add(next_priority)
                normalized[variant] = {
                    "name": variant,
                    "priority": next_priority,
                    "styles": {}
                }
                next_priority += 1
            else:
                name = variant["name"]
                priority = variant.get("priority", 1)
                if priority < 0:  # Handle negative priorities
                    while next_priority in used_priorities:
                        next_priority += 1
                    priority = next_priority
                    next_priority += 1
                while priority in used_priorities:  # Handle conflicts
                    priority += 1
                used_priorities.add(priority)
                normalized[name] = {
                    "name": name,
                    "priority": priority,
                    "styles": self._normalize_styles(variant.get("styles", {}))
                }
                
        return normalized

    def _normalize_states(self, states: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Normalize component states.
        
        Args:
            states: List of state configurations
            
        Returns:
            Normalized states
        """
        normalized = {}
        for state in states:
            if isinstance(state, str):
                normalized[state] = {
                    "name": state,
                    "priority": 1,
                    "styles": self._get_default_state_styles(state),
                    "transitions": {},
                    "accessibility": {}
                }
            else:
                name = state["name"]
                styles = self._normalize_styles(state.get("styles", {}))
                transitions = state.get("transitions", {})
                
                # Normalize transitions
                normalized_transitions = {}
                for prop, transition in transitions.items():
                    # Convert camelCase to kebab-case
                    normalized_prop = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', prop).lower()
                    
                    if isinstance(transition, str):
                        if transition == "fast":
                            normalized_transitions[normalized_prop] = {
                                "duration": "150ms",
                                "timing-function": "ease"
                            }
                        elif transition == "slow":
                            normalized_transitions[normalized_prop] = {
                                "duration": "300ms",
                                "timing-function": "ease"
                            }
                        elif transition == "0s" or transition == "0ms":
                            normalized_transitions[normalized_prop] = {
                                "duration": "0ms",
                                "timing-function": "ease"
                            }
                        else:
                            # Handle negative durations
                            is_negative = transition.startswith('-')
                            if is_negative:
                                normalized_transitions[normalized_prop] = {
                                    "duration": "0ms",
                                    "timing-function": "ease"
                                }
                                continue
                                
                            # Convert to milliseconds if in seconds
                            duration_ms = 0
                            if transition.endswith('s'):
                                try:
                                    seconds = float(transition[:-1])
                                    duration_ms = int(seconds * 1000)
                                except ValueError:
                                    duration_ms = 200  # Default duration
                            elif transition.endswith('ms'):
                                try:
                                    duration_ms = int(transition[:-2])
                                except ValueError:
                                    duration_ms = 200  # Default duration
                            else:
                                duration_ms = 200  # Default duration
                                
                            # Clamp duration between 0 and 1000ms
                            duration_ms = max(0, min(1000, duration_ms))
                            normalized_transitions[normalized_prop] = {
                                "duration": f"{duration_ms}ms",
                                "timing-function": "ease"
                            }
                    else:
                        duration = transition.get("duration", "200ms")
                        # Handle negative durations in dictionary format
                        if isinstance(duration, str) and duration.startswith('-'):
                            normalized_transitions[normalized_prop] = {
                                "duration": "0ms",
                                "timing-function": transition.get("timing-function", "ease")
                            }
                            continue
                            
                        # Convert duration to milliseconds and clamp
                        duration_ms = 200  # Default duration
                        if isinstance(duration, str):
                            if duration.endswith('s'):
                                try:
                                    seconds = float(duration[:-1])
                                    duration_ms = int(seconds * 1000)
                                except ValueError:
                                    pass
                            elif duration.endswith('ms'):
                                try:
                                    duration_ms = int(duration[:-2])
                                except ValueError:
                                    pass
                                    
                        # Clamp duration between 0 and 1000ms
                        duration_ms = max(0, min(1000, duration_ms))
                        normalized_transitions[normalized_prop] = {
                            "duration": f"{duration_ms}ms",
                            "timing-function": transition.get("timing-function", "ease")
                        }
                        
                normalized[name] = {
                    "name": name,
                    "priority": state.get("priority", 1),
                    "styles": styles,
                    "transitions": normalized_transitions,
                    "accessibility": state.get("accessibility", {})
                }
        
        return normalized

    def _normalize_accessibility(self, accessibility: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize accessibility configuration.
        
        Args:
            accessibility: Accessibility configuration
            
        Returns:
            Normalized accessibility configuration
        """
        self._validate_accessibility(accessibility)
        
        normalized = {
            "role": accessibility.get("role", ""),
            "aria-labels": accessibility.get("aria-labels", {}),
            "keyboard-interactions": {},
            "focus-management": {
                "tab-index": 0,
                "focus-visible": True
            }
        }
        
        # Normalize keyboard interactions
        if "keyboard-interactions" in accessibility:
            for key, value in accessibility["keyboard-interactions"].items():
                if isinstance(value, str):
                    normalized["keyboard-interactions"][key] = {
                        "action": value,
                        "description": f"Trigger {value} action"
                    }
                elif isinstance(value, dict):
                    normalized["keyboard-interactions"][key] = value
                    
        return normalized

    def _validate_typography(self, typography: Dict[str, Any]) -> None:
        """Validate typography values and emit warnings for invalid values.
        
        Args:
            typography: Typography configuration
        """
        if "fontSizes" in typography:
            for key, value in typography["fontSizes"].items():
                px = self._convert_to_px(value)
                if px is not None:
                    if px < 12:  # Too small for accessibility
                        warnings.warn(f"tiny: Font size is too small for accessibility ({value})")
                    elif px > 100:  # Unreasonably large
                        warnings.warn(f"huge: Font size is unreasonably large ({value})")
                else:
                    warnings.warn(f"invalid: Invalid font size unit ({value})")
                    
        if "lineHeights" in typography:
            for key, value in typography["lineHeights"].items():
                try:
                    height = float(value) if isinstance(value, (int, float)) else float(value[:-3])
                    if height < 1.0:
                        warnings.warn(f"cramped: Line height is too tight ({value})")
                    elif height > 3.0:
                        warnings.warn(f"airy: Line height is too loose ({value})")
                except (ValueError, TypeError, IndexError):
                    warnings.warn(f"invalid: Invalid line height value ({value})")
                    
        if "fontFamilies" in typography:
            for key, value in typography["fontFamilies"].items():
                if not isinstance(value, str):
                    warnings.warn(f"invalid: Invalid font family type ({value})")
                elif not value:
                    warnings.warn(f"missing: Empty font family value")
                elif ",," in value:
                    warnings.warn(f"empty-segments: Invalid font family list ({value})")
                elif any(c in value for c in ['"', "'"] if value.count(c) % 2 != 0):
                    warnings.warn(f"unclosed: Unclosed quotes in font family ({value})")

    def _validate_accessibility(self, accessibility: Dict[str, Any]) -> None:
        """Validate accessibility values and emit warnings for invalid values.
        
        Args:
            accessibility: Accessibility configuration
        """
        # Valid ARIA roles
        valid_roles = {
            "button", "link", "checkbox", "radio", "menuitem", "tab", "tabpanel",
            "dialog", "alert", "alertdialog", "banner", "complementary", "contentinfo",
            "form", "main", "navigation", "region", "search"
        }
        
        # Required ARIA attributes for specific roles
        required_attributes = {
            "checkbox": ["checked"],
            "radio": ["checked"],
            "tab": ["selected"],
            "tabpanel": ["labelledby"],
            "dialog": ["labelledby", "describedby"]
        }
        
        # Valid keyboard interactions
        valid_keys = {
            "enter", "space", "escape", "tab", "arrowup", "arrowdown",
            "arrowleft", "arrowright", "home", "end"
        }
        
        # Validate role
        if "role" in accessibility:
            role = accessibility["role"]
            if role not in valid_roles:
                warnings.warn(f"Invalid ARIA role: {role}")
                
            # Validate required attributes for the role
            if role in required_attributes:
                aria_labels = accessibility.get("aria-labels", {})
                for attr in required_attributes[role]:
                    if attr not in aria_labels:
                        warnings.warn(f"Missing required ARIA attribute: {attr} for role {role}")
                        
        # Validate keyboard interactions
        if "keyboard-interactions" in accessibility:
            for key, value in accessibility["keyboard-interactions"].items():
                if key.lower() not in valid_keys:
                    warnings.warn(f"Invalid keyboard interaction: {key}")
                if value is None:
                    warnings.warn(f"Invalid keyboard interaction value for {key}: None")
                    
        # Validate contrast ratio
        if "minimumContrast" in accessibility:
            try:
                contrast = float(accessibility["minimumContrast"])
                if contrast < 3.0:
                    warnings.warn(f"low: Contrast ratio is too low ({contrast})")
                elif contrast > 21.0:
                    warnings.warn(f"high: Contrast ratio is too high ({contrast})")
            except (ValueError, TypeError):
                warnings.warn(f"invalid: Invalid contrast ratio value ({accessibility['minimumContrast']})")
                
        # Validate target size
        if "targetSize" in accessibility:
            try:
                size = self._convert_to_px(accessibility["targetSize"])
                if size is not None:
                    if size < 44:  # WCAG recommendation
                        warnings.warn(f"small: Target size is too small ({accessibility['targetSize']})")
                    elif size > 100:
                        warnings.warn(f"large: Target size is too large ({accessibility['targetSize']})")
                else:
                    warnings.warn(f"invalid: Invalid target size unit ({accessibility['targetSize']})")
            except (ValueError, TypeError):
                warnings.warn(f"invalid: Invalid target size value ({accessibility['targetSize']})")

    def _validate_variant_priorities(self, variants: List[Union[str, Dict[str, Any]]]) -> None:
        """Validate variant priorities and emit warnings for invalid values.
        
        Args:
            variants: List of variant configurations
        """
        seen_priorities = set()
        for variant in variants:
            if isinstance(variant, dict) and "priority" in variant:
                try:
                    priority = int(variant["priority"])
                    if priority < 0:
                        warnings.warn(f"negative: Negative priority value ({priority})")
                    elif priority > 100:
                        warnings.warn(f"excessive: Priority value too high ({priority})")
                    elif priority in seen_priorities:
                        warnings.warn(f"duplicate: Duplicate priority value ({priority})")
                    else:
                        seen_priorities.add(priority)
                except (ValueError, TypeError):
                    warnings.warn(f"invalid: Invalid priority value ({variant['priority']})")

    def _get_default_state_styles(self, state: str) -> Dict[str, Any]:
        """Get default styles for a state.
        
        Args:
            state: State name
            
        Returns:
            Default styles
        """
        defaults = {
            "hover": {
                "opacity": 0.8,
                "transition": "opacity 150ms ease"
            },
            "active": {
                "transform": "scale(0.98)",
                "transition": "transform 150ms ease"
            },
            "focus": {
                "outline": "2px solid currentColor",
                "outline-offset": "2px"
            },
            "disabled": {
                "opacity": 0.5,
                "cursor": "not-allowed"
            }
        }
        return defaults.get(state, {})

    def _validate_colors(self, colors: Dict[str, Any]) -> None:
        """Validate color values and emit warnings for invalid values.
        
        Args:
            colors: Color configuration
        """
        for key, value in colors.items():
            if not isinstance(value, str):
                warnings.warn(f"invalid: Invalid color type ({value})")
                continue
                
            if not value:
                warnings.warn(f"missing: Empty color value")
                continue
                
            if not self._is_valid_color(value):
                warnings.warn(f"invalid: Invalid color format ({value})")
                continue
                
            if value.startswith('#'):
                rgb = self._hex_to_rgb(value)
                if rgb is not None:
                    brightness = sum(rgb) / (3 * 255)
                    if brightness < 0.1:
                        warnings.warn(f"dark: Color is too dark ({value})")
                    elif brightness > 0.9:
                        warnings.warn(f"light: Color is too light ({value})")

    def _normalize_color(self, value: str) -> str:
        """Normalize color value to hex format."""
        try:
            # Handle hex colors
            if value.startswith('#'):
                return value.lower()
                
            # Handle rgb/rgba colors
            if value.startswith('rgb'):
                rgb = [int(x.strip()) for x in value[value.find('(')+1:value.find(')')].split(',')[:3]]
                return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}".lower()
                
            # Handle named colors
            if value in self.color_names:
                return self.color_names[value].lower()
                
            return value
            
        except Exception as e:
            warnings.warn(f"error: Could not normalize color ({value}): {str(e)}")
            return value
            
    def _validate_style_values(self, styles: Dict[str, Any]) -> None:
        """Validate style values and emit warnings for invalid values."""
        for key, value in styles.items():
            if key.startswith('font-family'):
                if not isinstance(value, str):
                    warnings.warn(f"invalid: Invalid font family type ({value})")
                    
            elif key.startswith('font-size'):
                try:
                    size = self._convert_to_px(value)
                    if size is None:
                        warnings.warn(f"invalid: Invalid font size unit ({value})")
                    elif size < 8:
                        warnings.warn(f"tiny: Font size too small ({value})")
                    elif size > 100:
                        warnings.warn(f"huge: Font size too large ({value})")
                except (ValueError, TypeError):
                    warnings.warn(f"invalid: Invalid font size value ({value})")
                    
            elif key.startswith('font-weight'):
                try:
                    weight = int(value)
                    if weight < 100:
                        warnings.warn(f"light: Font weight too light ({value})")
                    elif weight > 900:
                        warnings.warn(f"heavy: Font weight too heavy ({value})")
                    elif weight % 100 != 0:
                        warnings.warn(f"invalid: Font weight not multiple of 100 ({value})")
                except (ValueError, TypeError):
                    warnings.warn(f"invalid: Invalid font weight value ({value})")
                    
            elif key.startswith('line-height'):
                try:
                    if isinstance(value, str):
                        if value.endswith('px'):
                            height = float(value[:-2])
                            if height < 10:
                                warnings.warn(f"cramped: Line height too tight ({value})")
                            elif height > 100:
                                warnings.warn(f"airy: Line height too loose ({value})")
                        elif value.endswith('em'):
                            height = float(value[:-2])
                            if height < 1.0:
                                warnings.warn(f"cramped: Line height too tight ({value})")
                            elif height > 3.0:
                                warnings.warn(f"airy: Line height too loose ({value})")
                        else:
                            warnings.warn(f"invalid: Invalid line height unit ({value})")
                    else:
                        height = float(value)
                        if height < 1.0:
                            warnings.warn(f"cramped: Line height too tight ({value})")
                        elif height > 3.0:
                            warnings.warn(f"airy: Line height too loose ({value})")
                except (ValueError, TypeError):
                    warnings.warn(f"invalid: Invalid line height value ({value})")
                    
            elif key.startswith('spacing'):
                try:
                    spacing = self._convert_to_px(value)
                    if spacing is None:
                        warnings.warn(f"invalid: Invalid spacing unit ({value})")
                    elif spacing < 0:
                        warnings.warn(f"negative: Negative spacing value ({value})")
                    elif spacing > 100:
                        warnings.warn(f"excessive: Spacing too large ({value})")
                except (ValueError, TypeError):
                    warnings.warn(f"invalid: Invalid spacing value ({value})")