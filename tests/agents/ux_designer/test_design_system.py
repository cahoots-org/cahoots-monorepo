import pytest
from datetime import datetime
from src.agents.ux_designer.design_system import DesignSystem
from typing import Dict, Any

@pytest.fixture
def design_system():
    config = {
        "version": "1.0",
        "model": "gpt-4-1106-preview",
        "brand_context": {
            "primary_color": "#007bff",
            "font_family": "Inter, system-ui, sans-serif"
        }
    }
    return DesignSystem(config)

class TestDesignSystemNormalization:
    """Test suite for design system normalization methods."""

    def test_normalize_colors(self, design_system):
        """Test color normalization with various formats."""
        colors = {
            "primary": "#07F",
            "secondary": "rgb(100, 120, 140)",
            "success": "hsl(120, 50%, 50%)",
            "error": "#FF0000",
            "invalid": "not-a-color"
        }
        
        normalized = design_system._normalize_colors(colors)
        
        assert normalized["primary"] == "#0077ff"
        assert normalized["secondary"].startswith("#")  # Should convert RGB to hex
        assert normalized["success"].startswith("#")    # Should convert HSL to hex
        assert normalized["error"] == "#ff0000"        # Should preserve valid hex
        assert normalized["invalid"] == "not-a-color"  # Should preserve invalid values
        
    def test_normalize_typography(self, design_system):
        """Test typography normalization."""
        typography = {
            "fontFamilies": {
                "body": "Inter,  system-ui,sans-serif",
                "heading": "Roboto, Arial"
            },
            "fontSizes": {
                "sm": "14px",
                "md": "1rem",
                "lg": "1.25em"
            },
            "fontWeights": {
                "normal": "regular",
                "bold": 700,
                "heavy": "black"
            },
            "lineHeights": {
                "tight": 1.2,
                "normal": "1.5",
                "loose": "2rem"
            }
        }
        
        normalized = design_system._normalize_typography(typography)
        
        # Test font families
        assert normalized["fontFamilies"]["body"] == "Inter, system-ui, sans-serif"
        assert normalized["fontFamilies"]["heading"] == "Roboto, Arial"
        
        # Test font sizes
        assert normalized["fontSizes"]["sm"] == "0.875rem"  # 14px -> 0.875rem
        assert normalized["fontSizes"]["md"] == "1rem"
        assert normalized["fontSizes"]["lg"] == "1.25rem"
        
        # Test font weights
        assert normalized["fontWeights"]["normal"] == 400
        assert normalized["fontWeights"]["bold"] == 700
        assert normalized["fontWeights"]["heavy"] == 900
        
        # Test line heights
        assert normalized["lineHeights"]["tight"] == 1.2
        assert normalized["lineHeights"]["normal"] == 1.5
        assert normalized["lineHeights"]["loose"] == 2
        
    def test_normalize_spacing(self, design_system):
        """Test spacing normalization."""
        spacing = {
            "xs": "4px",
            "sm": "0.5rem",
            "md": "16px",
            "lg": "2em",
            "xl": "32px"
        }
        
        normalized = design_system._normalize_spacing(spacing)
        
        assert normalized["xs"] == "0.25rem"   # 4px -> 0.25rem
        assert normalized["sm"] == "0.5rem"    # Already in rem
        assert normalized["md"] == "1rem"      # 16px -> 1rem
        assert normalized["lg"] == "2rem"      # 2em -> 2rem
        assert normalized["xl"] == "2rem"      # 32px -> 2rem
        
    def test_normalize_variants(self, design_system):
        """Test component variant normalization."""
        variants = [
            "primary",
            {
                "name": "secondary",
                "priority": 2,
                "styles": {
                    "backgroundColor": "#eee",
                    "fontSize": "14px"
                }
            }
        ]
        
        normalized = design_system._normalize_variants(variants)
        
        # Test string variant conversion
        assert "primary" in normalized
        assert normalized["primary"]["name"] == "primary"
        assert "priority" in normalized["primary"]
        assert "styles" in normalized["primary"]
        
        # Test object variant normalization
        assert normalized["secondary"]["name"] == "secondary"
        assert normalized["secondary"]["priority"] == 2
        assert normalized["secondary"]["styles"]["background-color"] == "#eeeeee"
        assert normalized["secondary"]["styles"]["font-size"] == "0.875rem"
        
    def test_normalize_states(self, design_system):
        """Test component state normalization."""
        states = [
            "hover",
            {
                "name": "active",
                "styles": {
                    "transform": "scale(0.98)",
                    "backgroundColor": "#0056b3"
                },
                "transitions": {
                    "transform": "fast",
                    "backgroundColor": {
                        "duration": "200ms",
                        "timing-function": "ease-out"
                    }
                }
            }
        ]
        
        normalized = design_system._normalize_states(states)
        
        # Test string state conversion
        assert "hover" in normalized
        assert normalized["hover"]["priority"] == 1
        assert "styles" in normalized["hover"]
        assert "transitions" in normalized["hover"]
        assert "accessibility" in normalized["hover"]
        
        # Test object state normalization
        assert normalized["active"]["styles"]["transform"] == "scale(0.98)"
        assert normalized["active"]["styles"]["background-color"] == "#0056b3"
        assert normalized["active"]["transitions"]["transform"]["duration"] == "150ms"
        assert normalized["active"]["transitions"]["background-color"]["duration"] == "200ms"
        
    def test_normalize_accessibility(self, design_system):
        """Test accessibility normalization."""
        accessibility = {
            "role": "button",
            "aria-labels": {
                "default": "Submit form",
                "loading": "Submitting..."
            },
            "keyboard-interactions": {
                "enter": "submit",
                "escape": {
                    "action": "cancel",
                    "description": "Cancels form submission"
                }
            }
        }
        
        normalized = design_system._normalize_accessibility(accessibility)
        
        assert normalized["role"] == "button"
        assert normalized["aria-labels"]["default"] == "Submit form"
        assert normalized["keyboard-interactions"]["enter"]["action"] == "submit"
        assert normalized["keyboard-interactions"]["escape"]["description"] == "Cancels form submission"
        assert "focus-management" in normalized
        
    @pytest.mark.parametrize("value,expected", [
        ("16px", 16.0),
        ("1.5rem", 24.0),
        ("24px", 24.0),
        ("100%", None),
        ("invalid", None)
    ])
    def test_convert_to_px(self, design_system, value, expected):
        """Test CSS unit conversion."""
        result = design_system._convert_to_px(value)
        assert result == expected

    @pytest.mark.parametrize("colors,expected", [
        # Test shorthand hex colors
        ({
            "primary": "#123",
            "secondary": "#ABC"
        }, {
            "primary": "#112233",
            "secondary": "#aabbcc"
        }),
        
        # Test invalid color formats
        ({
            "invalid1": "rgb(300, 400, 500)",  # Out of range RGB
            "invalid2": "hsl(400, 200%, 50%)", # Invalid HSL
            "invalid3": "currentColor",        # CSS keyword
            "invalid4": "var(--color)",        # CSS variable
            "invalid5": "",                    # Empty string
            "invalid6": None                   # None value
        }, {
            "invalid1": "rgb(300, 400, 500)",  # Preserve invalid
            "invalid2": "hsl(400, 200%, 50%)", # Preserve invalid
            "invalid3": "currentColor",        # Preserve keyword
            "invalid4": "var(--color)",        # Preserve variable
            "invalid5": "",                    # Preserve empty
            "invalid6": None                   # Preserve None
        }),
        
        # Test alpha channel handling
        ({
            "rgba": "rgba(255, 0, 0, 0.5)",
            "hsla": "hsla(120, 50%, 50%, 0.7)",
            "hexa": "#00ff0080"
        }, {
            "rgba": "#ff000080",
            "hsla": "#40bf40b2",
            "hexa": "#00ff0080"
        })
    ])
    def test_color_edge_cases(self, design_system, colors, expected):
        """Test color normalization edge cases."""
        normalized = design_system._normalize_colors(colors)
        for key, value in expected.items():
            assert normalized[key] == value

    @pytest.mark.parametrize("typography,expected_errors", [
        # Test invalid font sizes
        ({
            "fontSizes": {
                "tiny": "8px",        # Too small for accessibility
                "huge": "100rem",     # Unreasonably large
                "invalid": "large"    # Invalid unit
            }
        }, ["tiny", "huge", "invalid"]),
        
        # Test invalid line heights
        ({
            "lineHeights": {
                "cramped": 0.8,       # Too tight
                "airy": 3.5,          # Too loose
                "invalid": "normal"   # Invalid value
            }
        }, ["cramped", "airy", "invalid"]),
        
        # Test malformed font families
        ({
            "fontFamilies": {
                "missing": "",
                "invalid": 123,
                "unclosed": "Arial, 'Helvetica",
                "empty-segments": "Arial,,Helvetica"
            }
        }, ["missing", "invalid", "unclosed", "empty-segments"])
    ])
    def test_typography_validation_errors(self, design_system, typography, expected_errors):
        """Test typography validation error handling."""
        with pytest.warns(UserWarning) as warnings:
            normalized = design_system._normalize_typography(typography)
        
        warning_messages = [str(w.message) for w in warnings]
        for error in expected_errors:
            assert any(error in msg for msg in warning_messages)

    @pytest.mark.parametrize("spacing,expected", [
        # Test negative values
        ({
            "negative": "-1rem",
            "negative-px": "-16px"
        }, {
            "negative": "0rem",      # Should clamp to 0
            "negative-px": "0rem"    # Should clamp to 0
        }),
        
        # Test calc() expressions
        ({
            "calc1": "calc(1rem + 8px)",
            "calc2": "calc(100% - 20px)",
            "calc3": "calc(50vw / 2)"
        }, {
            "calc1": "calc(1rem + 8px)",  # Preserve calc
            "calc2": "calc(100% - 20px)", # Preserve calc
            "calc3": "calc(50vw / 2)"     # Preserve calc
        }),
        
        # Test CSS custom properties
        ({
            "custom1": "var(--spacing)",
            "custom2": "var(--spacing, 1rem)"
        }, {
            "custom1": "var(--spacing)",         # Preserve custom property
            "custom2": "var(--spacing, 1rem)"    # Preserve custom property
        }),
        
        # Test mixed units
        ({
            "mixed1": "calc(1rem + 8px)",
            "mixed2": "16px + 1rem",    # Invalid
            "mixed3": "1rem1rem"        # Invalid
        }, {
            "mixed1": "calc(1rem + 8px)",
            "mixed2": "1rem",           # Fallback to base
            "mixed3": "1rem"            # Fallback to base
        })
    ])
    def test_spacing_edge_cases(self, design_system, spacing, expected):
        """Test spacing normalization edge cases."""
        normalized = design_system._normalize_spacing(spacing)
        assert normalized == expected

    def test_variant_priority_conflicts(self, design_system):
        """Test handling of variant priority conflicts."""
        variants = [
            {
                "name": "primary",
                "priority": 1
            },
            {
                "name": "secondary",
                "priority": 1  # Same priority as primary
            },
            {
                "name": "tertiary",
                "priority": -1  # Invalid priority
            }
        ]
        
        with pytest.warns(UserWarning) as warnings:
            normalized = design_system._normalize_variants(variants)
        
        assert normalized["primary"]["priority"] == 1
        assert normalized["secondary"]["priority"] == 2  # Auto-incremented
        assert normalized["tertiary"]["priority"] == 3   # Auto-incremented

    def test_state_transition_edge_cases(self, design_system):
        """Test state transition normalization edge cases."""
        states = [
            {
                "name": "hover",
                "transitions": {
                    "instant": "0s",
                    "negative": "-200ms",
                    "huge": "10000ms",
                    "invalid": "fast-ish",
                    "complex": "200ms ease-in-out 100ms"
                }
            }
        ]
        
        normalized = design_system._normalize_states(states)
        transitions = normalized["hover"]["transitions"]
        
        assert transitions["instant"]["duration"] == "0ms"
        assert transitions["negative"]["duration"] == "0ms"  # Clamp to 0
        assert transitions["huge"]["duration"] == "200ms"  # Clamp to max
        assert transitions["invalid"]["duration"] == "250ms"  # Fallback to normal
        assert transitions["complex"]["duration"] == "200ms"
        assert transitions["complex"]["delay"] == "100ms"

    @pytest.mark.parametrize("accessibility,expected_warnings", [
        # Test invalid ARIA roles
        ({
            "role": "invalid-role",
            "aria-labels": {"default": "Label"}
        }, ["Invalid ARIA role"]),
        
        # Test missing required ARIA attributes
        ({
            "role": "checkbox",
            "aria-labels": {}  # Missing required checked state
        }, ["Missing required ARIA attribute"]),
        
        # Test invalid keyboard interactions
        ({
            "keyboard-interactions": {
                "invalid-key": "action",
                "space": None
            }
        }, ["Invalid keyboard interaction"])
    ])
    def test_accessibility_validation(self, design_system, accessibility, expected_warnings):
        """Test accessibility validation and warnings."""
        with pytest.warns(UserWarning) as warnings:
            normalized = design_system._normalize_accessibility(accessibility)
        
        warning_messages = [str(w.message) for w in warnings]
        for expected in expected_warnings:
            assert any(expected in msg for msg in warning_messages)

    def test_normalize_empty_inputs(self, design_system):
        """Test normalization with empty or minimal inputs."""
        assert design_system._normalize_colors({}) == {}
        assert "fontFamilies" in design_system._normalize_typography({})
        assert design_system._normalize_spacing({}) == {}
        assert design_system._normalize_variants([]) == {}
        assert design_system._normalize_states([]) == {}
        assert "role" in design_system._normalize_accessibility({}) 