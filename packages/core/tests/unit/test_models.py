"""Unit tests for core data models."""
import pytest
from core.models import AgentConfig, TeamDynamics, TeamConfig

def test_agent_config_creation():
    """Test creating an agent configuration"""
    config = AgentConfig(
        name="Test Agent",
        type="test",
        model_name="test-model",
        events={
            "listen": ["event1", "event2"],
            "publish": ["event3"]
        },
        capabilities={
            "test_capability": {
                "feature": "value"
            }
        }
    )
    
    assert config.name == "Test Agent"
    assert config.type == "test"
    assert config.model_name == "test-model"
    assert "event1" in config.events["listen"]
    assert "event3" in config.events["publish"]
    assert config.capabilities["test_capability"]["feature"] == "value"

def test_team_dynamics_creation():
    """Test creating team dynamics configuration"""
    dynamics = TeamDynamics(
        collaboration_patterns={
            "code_review": {
                "required_reviewers": ["developer", "qa"]
            }
        },
        communication_channels={
            "developer": ["pr_created", "code_review_completed"],
            "qa": ["test_completed", "bug_found"]
        }
    )
    
    assert "code_review" in dynamics.collaboration_patterns
    assert "developer" in dynamics.communication_channels
    assert "pr_created" in dynamics.communication_channels["developer"]

def test_team_config_creation():
    """Test creating team configuration"""
    agent_config = AgentConfig(
        name="Test Agent",
        type="test",
        model_name="test-model",
        events={
            "listen": ["event1"],
            "publish": ["event2"]
        }
    )
    
    dynamics = TeamDynamics(
        collaboration_patterns={
            "code_review": {
                "required_reviewers": ["developer"]
            }
        },
        communication_channels={
            "developer": ["pr_created"]
        }
    )
    
    config = TeamConfig(
        project_id="test-project",
        agents={"test_agent": agent_config},
        team_dynamics=dynamics
    )
    
    assert config.project_id == "test-project"
    assert "test_agent" in config.agents
    assert config.team_dynamics.collaboration_patterns["code_review"]["required_reviewers"] == ["developer"]

def test_agent_config_validation():
    """Test validation of agent configuration"""
    with pytest.raises(ValueError):
        # Missing required fields
        AgentConfig()
        
    with pytest.raises(ValueError):
        # Invalid event structure
        AgentConfig(
            name="Test",
            type="test",
            model_name="test",
            events="invalid"
        )

def test_team_config_without_dynamics():
    """Test team configuration without dynamics"""
    agent_config = AgentConfig(
        name="Test Agent",
        type="test",
        model_name="test-model",
        events={
            "listen": ["event1"],
            "publish": ["event2"]
        }
    )
    
    config = TeamConfig(
        project_id="test-project",
        agents={"test_agent": agent_config}
    )
    
    assert config.team_dynamics is None 