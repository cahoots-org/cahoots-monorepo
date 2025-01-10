"""Tests for the Model class."""
import pytest
from typing import TYPE_CHECKING, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
import json

from src.utils.model import Model
from src.utils.config import Config, ServiceConfig

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

@pytest.fixture
def mock_together_service() -> ServiceConfig:
    """Create a mock Together service config."""
    return ServiceConfig(
        name="together",
        url="https://api.together.xyz",
        timeout=30,
        retry_attempts=3,
        retry_delay=1,
        api_key="test_api_key"
    )

@pytest.fixture
def mock_config(monkeypatch: pytest.MonkeyPatch, mock_together_service: ServiceConfig) -> None:
    """Mock the config module."""
    services = {"together": mock_together_service}
    monkeypatch.setattr("src.utils.config.config.services", services)

@pytest.mark.asyncio
async def test_model_initialization(mock_config: None) -> None:
    """Test model initialization."""
    model = Model("test-model")
    assert model.model_name == "test-model"
    assert model.api_key == "test_api_key"
    assert model.api_base == "https://api.together.xyz/chat/completions"
    assert model.headers == {
        "Authorization": "Bearer test_api_key",
        "Content-Type": "application/json"
    }

@pytest.mark.asyncio
async def test_model_initialization_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test model initialization with no API key."""
    services: Dict[str, Any] = {}
    monkeypatch.setattr("src.utils.config.config.services", services)
    
    with pytest.raises(RuntimeError, match="Together service not configured"):
        Model("test-model")
        
    # Test with empty API key
    services = {
        "together": ServiceConfig(
            name="together",
            url="https://api.together.xyz",
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            api_key=""
        )
    }
    monkeypatch.setattr("src.utils.config.config.services", services)
    
    with pytest.raises(RuntimeError, match="Together API key not configured"):
        Model("test-model")

class MockResponse:
    """Mock aiohttp response."""
    def __init__(self, status: int, json_data: Dict[str, Any] = None, text: str = None):
        self.status = status
        self._json = json_data
        self._text = text
        
    async def json(self) -> Dict[str, Any]:
        if isinstance(self._json, Exception):
            raise self._json
        return self._json
        
    async def text(self) -> str:
        return self._text
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MockClientSession:
    """Mock aiohttp ClientSession."""
    def __init__(self, response: MockResponse):
        self.response = response
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def post(self, *args, **kwargs):
        """Mock post request."""
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

@pytest.mark.asyncio
async def test_generate_response(mock_config: None) -> None:
    """Test successful response generation."""
    model = Model("test-model")
    
    # Mock successful response
    mock_response = MockResponse(
        status=200,
        json_data={
            "choices": [{
                "message": {
                    "content": "Test response"
                }
            }]
        }
    )
    
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        response = await model.generate_response("Test prompt")
        assert response == "Test response"
        
@pytest.mark.asyncio
async def test_generate_response_api_error(mock_config: None) -> None:
    """Test API error handling."""
    model = Model("test-model")
    
    # Mock error response
    mock_response = MockResponse(
        status=400,
        text="Bad request"
    )
    
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(RuntimeError, match="API request failed: Bad request"):
            await model.generate_response("Test prompt")

@pytest.mark.asyncio
async def test_generate_response_connection_error(mock_config: None) -> None:
    """Test connection error handling."""
    model = Model("test-model")
    
    # Mock session with connection error
    mock_session = MockClientSession(aiohttp.ClientError("Connection failed"))
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(RuntimeError, match="Failed to connect to API: Connection failed"):
            await model.generate_response("Test prompt")

@pytest.mark.asyncio
async def test_generate_response_invalid_json(mock_config: None) -> None:
    """Test invalid JSON response handling."""
    model = Model("test-model")
    
    # Mock invalid JSON response
    mock_response = MockResponse(
        status=200,
        json_data={"invalid": "response"}  # Missing required fields
    )
    
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(RuntimeError, match="Invalid API response"):
            await model.generate_response("Test prompt") 