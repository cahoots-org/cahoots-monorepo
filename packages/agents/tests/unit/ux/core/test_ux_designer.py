"""Unit tests for the UX designer."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import json
import os

from cahoots_core.models.task import Task
from cahoots_core.models.team_config import TeamConfig
from src.cahoots_agents.ux.core.ux_designer import UXDesigner
from src.cahoots_agents.ux.design.design_system import DesignSystem
from src.cahoots_agents.ux.patterns.pattern_library import PatternLibrary
from cahoots_core.utils.config.base import ServiceConfig

@pytest.fixture
def mock_team_config():
    """Create mock team config."""
    config = MagicMock(spec=TeamConfig)
    config.roles = {
        "ux_designer": {
            "model_name": "test-model",
            "capabilities": ["design", "accessibility", "patterns"]
        }
    }
    return config

@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = MagicMock()
    # Set up the config with proper AI provider structure
    agent.config = {
        "ai": {
            "provider": "test",
            "api_key": "test-key",
            "models": {
                "default": "test-model",
                "fallback": "test-model-fallback"
            }
        }
    }
    agent.get.return_value = agent.config
    agent.generate_response = AsyncMock()
    agent.stream_response = AsyncMock(return_value=["chunk1", "chunk2"])
    return agent

@pytest.fixture
def mock_design_system():
    """Create mock design system."""
    system = Mock(spec=DesignSystem)
    system.get_component = AsyncMock()
    system.get_color_scheme = AsyncMock()
    system.get_typography = AsyncMock()
    return system

@pytest.fixture
def mock_pattern_library():
    """Create mock pattern library."""
    library = Mock(spec=PatternLibrary)
    library.get_pattern = AsyncMock()
    library.get_best_practices = AsyncMock()
    return library

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    return Mock()

@pytest.fixture
def mock_github_config():
    """Create mock GitHub config."""
    return ServiceConfig(
        name="test-github",
        url="https://api.github.com",
        api_key="test-github-key",
        workspace_dir="/tmp/test",
        repo_name="test-repo"
    )

@pytest.fixture
async def ux_designer(mock_agent, mock_event_system, mock_team_config, mock_github_config, mock_design_system, mock_pattern_library):
    """Create UX designer with mocked dependencies."""
    with patch('cahoots_core.models.team_config.TeamConfig.from_env', return_value=mock_team_config):
        with patch.dict(os.environ, {"DESIGNER_ID": "test-designer"}):
            designer = UXDesigner(
                event_system=mock_event_system,
                github_config=mock_github_config,
                start_listening=False  # Don't auto-start event system in tests
            )
            # Set up mock agent
            designer.agent = mock_agent
            designer.design_system = mock_design_system
            designer.pattern_library = mock_pattern_library
            
            # Initialize async components
            await designer.start()
            return designer

@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id="task1",
        title="Design login form",
        description="Create user-friendly login form",
        metadata={
            "requirements": {
                "fields": ["email", "password"],
                "accessibility": "WCAG 2.1"
            }
        }
    )

@pytest.mark.asyncio
async def test_generate_design_success(ux_designer, sample_task):
    """Test successful design generation."""
    designer = await ux_designer
    expected_design = {
        "components": [
            {
                "type": "form",
                "fields": [
                    {
                        "type": "email",
                        "label": "Email",
                        "validation": ["required", "email"]
                    },
                    {
                        "type": "password",
                        "label": "Password",
                        "validation": ["required", "min:8"]
                    }
                ],
                "actions": [
                    {
                        "type": "button",
                        "label": "Log In",
                        "variant": "primary"
                    }
                ]
            }
        ],
        "styles": {
            "colors": {"primary": "#007AFF"},
            "typography": {"font-family": "Inter"}
        }
    }
    designer.agent.generate_response.return_value = json.dumps(expected_design)
    
    design: Dict[str, Any] = await designer.generate_design(sample_task)
    
    assert design.get("components")[0].get("type") == "form"
    assert len(design.get("components")[0].get("fields")) == 2

@pytest.mark.asyncio
async def test_generate_design_invalid_json(ux_designer, sample_task):
    """Test handling of invalid JSON response."""
    designer = await ux_designer
    designer.agent.generate_response.return_value = "invalid json"
    
    with pytest.raises(ValueError, match="Failed to parse design"):
        await designer.generate_design(sample_task)

@pytest.mark.asyncio
async def test_validate_accessibility(ux_designer):
    """Test accessibility validation."""
    designer = await ux_designer
    design = {
        "components": [
            {
                "type": "button",
                "label": "Submit",
                "color": "#FFFFFF",
                "background": "#007AFF"
            }
        ]
    }
    expected_validation = {
        "valid": True,
        "warnings": [
            {
                "component": "button",
                "issue": "Color contrast ratio is 4.2:1, minimum required is 4.5:1",
                "recommendation": "Darken background color to #0066CC"
            }
        ]
    }
    designer.agent.generate_response.return_value = json.dumps(expected_validation)
    
    validation = await designer.validate_accessibility(design)
    
    assert validation.get("valid")
    assert len(validation.get("warnings")) > 0

@pytest.mark.asyncio
async def test_generate_component_variants(ux_designer):
    """Test component variant generation."""
    designer = await ux_designer
    component = {
        "type": "button",
        "label": "Submit"
    }
    expected_variants = {
        "variants": [
            {
                "name": "primary",
                "styles": {"background": "#007AFF", "color": "#FFFFFF"}
            },
            {
                "name": "secondary",
                "styles": {"background": "transparent", "border": "1px solid #007AFF"}
            },
            {
                "name": "danger",
                "styles": {"background": "#FF3B30", "color": "#FFFFFF"}
            }
        ]
    }
    designer.agent.generate_response.return_value = json.dumps(expected_variants)
    
    variants = await designer.generate_component_variants(component)
    
    assert len(variants.get("variants")) == 3
    assert all("styles" in v for v in variants.get("variants"))

@pytest.mark.asyncio
async def test_apply_design_system(ux_designer):
    """Test design system application."""
    designer = await ux_designer
    design = {
        "components": [
            {
                "type": "button",
                "label": "Submit"
            }
        ]
    }
    system_styles = {
        "colors": {"primary": "#007AFF"},
        "typography": {"font-family": "Inter"}
    }
    designer.design_system.get_color_scheme.return_value = system_styles["colors"]
    designer.design_system.get_typography.return_value = system_styles["typography"]
    
    styled_design = await designer.apply_design_system(design)
    
    assert "styles" in styled_design
    assert styled_design.get("styles").get("colors") == system_styles.get("colors")
    assert styled_design.get("styles").get("typography") == system_styles.get("typography")

@pytest.mark.asyncio
async def test_generate_responsive_layout(ux_designer):
    """Test responsive layout generation."""
    designer = await ux_designer
    components = [
        {"type": "header", "content": "Login"},
        {"type": "form", "fields": []}
    ]
    expected_layout = {
        "desktop": {
            "grid": "1fr 1fr",
            "gap": "2rem",
            "components": [
                {"gridColumn": "1 / -1", "component": components[0]},
                {"gridColumn": "1 / 2", "component": components[1]}
            ]
        },
        "mobile": {
            "grid": "1fr",
            "gap": "1rem",
            "components": [
                {"gridColumn": "1", "component": components[0]},
                {"gridColumn": "1", "component": components[1]}
            ]
        }
    }
    designer.agent.generate_response.return_value = json.dumps(expected_layout)
    
    layout = await designer.generate_responsive_layout(components)
    
    assert "desktop" in layout
    assert "mobile" in layout
    assert len(layout["desktop"]["components"]) == 2
    assert len(layout["mobile"]["components"]) == 2

@pytest.mark.asyncio
async def test_generate_interaction_states(ux_designer):
    """Test interaction state generation."""
    designer = await ux_designer
    component = {
        "type": "button",
        "label": "Submit"
    }
    expected_states = {
        "states": [
            {
                "name": "hover",
                "styles": {"background": "#0066CC"}
            },
            {
                "name": "active",
                "styles": {"background": "#005299"}
            },
            {
                "name": "disabled",
                "styles": {"background": "#E5E5EA", "cursor": "not-allowed"}
            }
        ]
    }
    designer.agent.generate_response.return_value = json.dumps(expected_states)
    
    states = await designer.generate_interaction_states(component)
    
    assert len(states["states"]) == 3
    assert all("styles" in state for state in states["states"]) 