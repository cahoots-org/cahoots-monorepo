"""Unit tests for base agent functionality."""
import pytest
from unittest.mock import Mock, AsyncMock
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.cahoots_agents.base import BaseAgent

@pytest.fixture
def mock_ai_provider():
    """Create mock AI provider."""
    provider = Mock()
    provider.generate_response = AsyncMock(return_value="Test response")
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["chunk1", "chunk2"]:
            yield chunk
    
    provider.stream_response = mock_stream
    return provider

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    system = Mock()
    system.publish = AsyncMock()
    return system

@pytest.fixture
def config():
    """Create test configuration."""
    return {
        "ai": {
            "provider": "test",
            "api_key": "test-key",
            "models": {
                "default": "test-model",
                "fallback": "fallback-model"
            },
            "settings": {
                "temperature": 0.7
            }
        },
        "agents": {
            "test": {
                "model": "test-model",
                "temperature": 0.7
            }
        }
    }

@pytest.fixture
def base_agent(config, mock_event_system, mock_ai_provider):
    """Create base agent instance."""
    agent = BaseAgent(
        agent_type="test",
        event_system=mock_event_system,
        config=config,
        ai_provider=mock_ai_provider
    )
    return agent

def test_agent_initialization(base_agent, config, mock_event_system):
    """Test agent initialization."""
    assert base_agent.agent_type == "test"
    assert base_agent.event_system == mock_event_system
    assert base_agent.config == config

def test_agent_initialization_defaults(mock_ai_provider, mock_event_system, config):
    """Test agent initialization with defaults."""
    agent = BaseAgent(
        agent_type="test",
        event_system=mock_event_system,
        config=config,
        ai_provider=mock_ai_provider
    )
    assert agent.agent_type == "test"
    assert agent.event_system == mock_event_system
    assert agent.config == config
    assert agent.ai == mock_ai_provider

@pytest.mark.asyncio
async def test_generate_response(base_agent):
    """Test response generation."""
    prompt = "Test prompt"
    response = await base_agent.generate_response(prompt)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_generate_response_with_fallback(base_agent):
    """Test response generation with fallback."""
    prompt = "Test prompt"
    base_agent.ai.generate_response.side_effect = [
        Exception("First attempt failed"),
        "Fallback response"
    ]
    response = await base_agent.generate_response(prompt)
    assert response == "Fallback response"

@pytest.mark.asyncio
async def test_generate_response_error_no_fallback(base_agent):
    """Test response generation error without fallback."""
    prompt = "Test prompt"
    base_agent.ai.generate_response.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        await base_agent.generate_response(prompt)

@pytest.mark.asyncio
async def test_generate_embeddings(base_agent):
    """Test embedding generation."""
    texts = ["Test text 1", "Test text 2"]
    base_agent.ai.generate_embeddings = AsyncMock(
        return_value=[[0.1, 0.2], [0.3, 0.4]]
    )
    embeddings = await base_agent.generate_embeddings(texts)
    assert len(embeddings) == 2
    assert all(isinstance(emb, list) for emb in embeddings)

@pytest.mark.asyncio
async def test_stream_response(base_agent):
    """Test response streaming."""
    chunks = []
    async for chunk in base_agent.stream_response("Test prompt"):
        chunks.append(chunk)
    assert chunks == ["chunk1", "chunk2"]

@pytest.mark.asyncio
async def test_generate_response_with_kwargs(base_agent):
    """Test response generation with additional kwargs."""
    prompt = "Test prompt"
    kwargs = {
        "temperature": 0.5,
        "max_tokens": 100
    }
    await base_agent.generate_response(prompt, **kwargs)
    base_agent.ai.generate_response.assert_called_once_with(
        prompt,
        temperature=0.5,
        max_tokens=100,
        model="test-model"
    )

@pytest.mark.asyncio
async def test_stream_response_with_kwargs(base_agent):
    """Test response streaming with additional kwargs."""
    chunks = []
    async for chunk in base_agent.stream_response("Test prompt", temperature=0.5, max_tokens=100):
        chunks.append(chunk)
    assert chunks == ["chunk1", "chunk2"] 