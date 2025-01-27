"""Tests for context selection."""
import pytest
from unittest.mock import patch, mock_open, Mock, AsyncMock
import json

from cahoots_context.manager.context_selection import (
    ContextVariables, ContextActions, ContextAgent,
    ContextChannel, ContextRuleEngine, ContextSelectionService
)

@pytest.fixture
def sample_facts():
    """Create sample facts for testing."""
    return {
        "status": "approved",
        "request_type": "feature",
        "impact": "high",
        "age_days": 5,
        "priority": "high"
    }

@pytest.fixture
def sample_agent_config():
    """Create sample agent configuration."""
    return {
        "name": "test_agent",
        "enabled": True,
        "capabilities": ["test", "review"],
        "channels": ["channel1", "channel2"],
        "priority": 100,
        "max_items": 50,
        "memory_size": 1000,
        "context_window": 2000,
        "rules": ["test_rules.json"]
    }

@pytest.fixture
def sample_channel_config():
    """Create sample channel configuration."""
    return {
        "name": "test_channel",
        "enabled": True,
        "priority": 100,
        "events": ["event1", "event2"],
        "max_items": 50,
        "rules": ["test_rules.json"],
        "required_capabilities": ["test", "review"]
    }

def test_context_variables(sample_facts):
    """Test ContextVariables class."""
    variables = ContextVariables(sample_facts)
    
    assert variables.status() == "approved"
    assert variables.request_type() == "feature"
    assert variables.impact() == "high"
    assert variables.age_days() == 5
    assert variables.priority() == "high"
    
    # Test missing facts
    empty_variables = ContextVariables({})
    assert empty_variables.status() is None
    assert empty_variables.age_days() == 0

def test_context_actions():
    """Test ContextActions class."""
    actions = ContextActions()
    
    # Test initial score
    assert actions.get_score() == 0
    
    # Test adding points
    actions.add_score(100)
    assert actions.get_score() == 100
    
    # Test multiple additions
    actions.add_score(50)
    assert actions.get_score() == 150
    
    # Test negative points
    actions.add_score(-30)
    assert actions.get_score() == 120

def test_context_agent(sample_agent_config):
    """Test ContextAgent class."""
    agent = ContextAgent(sample_agent_config)
    
    # Test initialization
    assert agent.name == "test_agent"
    assert agent.enabled is True
    assert "test" in agent.capabilities
    assert "review" in agent.capabilities
    assert "channel1" in agent.channels
    assert "channel2" in agent.channels
    assert agent.priority == 100
    assert agent.max_items == 50
    assert agent.memory_size == 1000
    assert agent.context_window == 2000
    
    # Test capability handling
    assert agent.can_handle("channel1", "test") is True
    assert agent.can_handle("channel2", "review") is True
    assert agent.can_handle("channel3", "test") is False
    assert agent.can_handle("channel1", "unknown") is False
    
    # Test wildcard channel
    agent.channels = {"*"}
    assert agent.can_handle("any_channel", "test") is True
    
    # Test wildcard capability
    agent.capabilities = {"*"}
    assert agent.can_handle("any_channel", "any_capability") is True

def test_context_channel(sample_channel_config):
    """Test ContextChannel class."""
    channel = ContextChannel(sample_channel_config)
    
    # Test initialization
    assert channel.name == "test_channel"
    assert channel.enabled is True
    assert channel.priority == 100
    assert "event1" in channel.events
    assert "event2" in channel.events
    assert channel.max_items == 50
    assert "test" in channel.required_capabilities
    assert "review" in channel.required_capabilities
    
    # Test default values
    minimal_channel = ContextChannel({"name": "minimal"})
    assert minimal_channel.enabled is True
    assert minimal_channel.priority == 0
    assert minimal_channel.max_items == 50
    assert len(minimal_channel.required_capabilities) == 0

@pytest.mark.asyncio
async def test_context_rule_engine_run(sample_facts):
    """Test ContextRuleEngine rule execution."""
    engine = ContextRuleEngine()

    # Add a test rule
    engine.rules = [{
        "conditions": {
            "all": [{
                "name": "status",
                "operator": "equal_to",
                "value": "approved"
            }]
        },
        "actions": [
            {
                "name": "add_score",
                "params": {"points": 100}
            }
        ]
    }]

    # Run rules
    result = engine.run(sample_facts)
    assert result["success"] is True
    assert result["score"] == 100

@pytest.mark.asyncio
async def test_context_rule_engine_initialization():
    """Test ContextRuleEngine initialization and config loading."""
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("builtins.open", mock_open(read_data="[]")) as mock_file:

        # Test creating default config when directory doesn't exist
        mock_exists.return_value = False
        engine = ContextRuleEngine()
        
        # Verify mkdir was called
        mock_mkdir.assert_called_once()
        
        # Verify default config was written
        assert mock_file.call_count > 0

@pytest.mark.asyncio
async def test_context_rule_engine_default_config():
    """Test ContextRuleEngine default configuration creation."""
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("builtins.open", mock_open(read_data="[]")) as mock_file:

        mock_exists.return_value = False
        engine = ContextRuleEngine()
        
        # Verify default agents were created
        assert len(engine.agents) == 0  # No agents loaded from empty mock file
        
        # Verify default channels were created
        assert len(engine.channels) == 0  # No channels loaded from empty mock file

@pytest.mark.asyncio
async def test_context_channel():
    """Test ContextChannel initialization and properties."""
    config = {
        "name": "test_channel",
        "enabled": True,
        "priority": 100,
        "events": ["event1", "event2"],
        "max_items": 10,
        "rules": ["rule1.json"],
        "required_capabilities": ["cap1", "cap2"]
    }
    
    channel = ContextChannel(config)
    assert channel.name == "test_channel"
    assert channel.enabled is True
    assert channel.priority == 100
    assert "event1" in channel.events
    assert channel.max_items == 10
    assert "rule1.json" in channel.rules
    assert "cap1" in channel.required_capabilities

@pytest.mark.asyncio
async def test_context_agent():
    """Test ContextAgent initialization and capabilities."""
    config = {
        "name": "test_agent",
        "enabled": True,
        "capabilities": ["cap1", "cap2"],
        "channels": ["channel1"],
        "priority": 100,
        "max_items": 10,
        "memory_size": 1000,
        "context_window": 2000
    }
    
    agent = ContextAgent(config)
    assert agent.name == "test_agent"
    assert agent.enabled is True
    assert "cap1" in agent.capabilities
    assert "channel1" in agent.channels
    assert agent.priority == 100
    assert agent.max_items == 10
    assert agent.memory_size == 1000
    assert agent.context_window == 2000
    
    # Test capability handling
    assert agent.can_handle("channel1", "cap1") is True
    assert agent.can_handle("channel2", "cap1") is False
    assert agent.can_handle("channel1", "cap3") is False

@pytest.mark.asyncio
async def test_context_actions():
    """Test ContextActions score management."""
    actions = ContextActions()
    
    # Test initial score
    assert actions.get_score() == 0
    
    # Test adding points
    actions.add_score(100)
    assert actions.get_score() == 100
    
    actions.add_score(50)
    assert actions.get_score() == 150

@pytest.mark.asyncio
async def test_context_variables():
    """Test ContextVariables fact access."""
    facts = {
        "status": "approved",
        "request_type": "feature",
        "impact": "high",
        "age_days": 5,
        "priority": "high"
    }
    
    variables = ContextVariables(facts)
    assert variables.status() == "approved"
    assert variables.request_type() == "feature"
    assert variables.impact() == "high"
    assert variables.age_days() == 5
    assert variables.priority() == "high" 