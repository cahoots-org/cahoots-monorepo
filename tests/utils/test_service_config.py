"""Tests for configuration management."""
import os
import pytest
from src.utils.config import ServiceConfig, TrelloConfig
from src.utils.exceptions import ConfigurationError

def test_service_config():
    """Test service config creation."""
    config = ServiceConfig(
        name="test",
        url="http://test.com",
        timeout=30,
        retry_attempts=3,
        retry_delay=1
    )
    assert config.name == "test"
    assert config.url == "http://test.com"
    assert config.timeout == 30
    assert config.retry_attempts == 3
    assert config.retry_delay == 1
    assert config.api_key is None

def test_service_config_validation():
    """Test service config validation."""
    # Test invalid timeout
    with pytest.raises(ConfigurationError, match="Timeout must be positive"):
        ServiceConfig(
            name="test",
            url="http://test.com",
            timeout=0
        )
        
    # Test invalid retry attempts
    with pytest.raises(ConfigurationError, match="Retry attempts must be non-negative"):
        ServiceConfig(
            name="test",
            url="http://test.com",
            retry_attempts=-1
        )
        
    # Test invalid retry delay
    with pytest.raises(ConfigurationError, match="Retry delay must be positive"):
        ServiceConfig(
            name="test",
            url="http://test.com",
            retry_delay=0
        )

def test_service_config_from_dict():
    """Test creating service config from dict."""
    data = {
        "name": "test",
        "url": "http://test.com",
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 1
    }
    config = ServiceConfig.from_dict(data)
    assert config.name == "test"
    assert config.url == "http://test.com"
    assert config.timeout == 30
    assert config.retry_attempts == 3
    assert config.retry_delay == 1
    
    # Test invalid data
    with pytest.raises(ConfigurationError, match="Invalid service configuration"):
        ServiceConfig.from_dict({"invalid": "data"})

def test_service_config_from_env():
    """Test creating service config from environment variables."""
    os.environ["TEST_NAME"] = "test"
    os.environ["TEST_URL"] = "http://test.com"
    os.environ["TEST_TIMEOUT"] = "30"
    os.environ["TEST_RETRY_ATTEMPTS"] = "3"
    os.environ["TEST_RETRY_DELAY"] = "1"
    
    config = ServiceConfig.from_env("TEST_")
    assert config.name == "test"
    assert config.url == "http://test.com"
    assert config.timeout == 30
    assert config.retry_attempts == 3
    assert config.retry_delay == 1
    
    # Clean up
    del os.environ["TEST_NAME"]
    del os.environ["TEST_URL"]
    del os.environ["TEST_TIMEOUT"]
    del os.environ["TEST_RETRY_ATTEMPTS"]
    del os.environ["TEST_RETRY_DELAY"]

def test_trello_config_validation():
    """Test Trello config validation."""
    # Test valid config
    config = TrelloConfig(
        name="trello",
        url="https://api.trello.com/1",
        api_key="test-key",
        api_token="test-token",
        organization_id="test-org",
        board_template_id="test-board"
    )
    assert config.name == "trello"
    assert config.url == "https://api.trello.com/1"
    assert config.api_key == "test-key"
    assert config.api_token == "test-token"
    assert config.organization_id == "test-org"
    assert config.board_template_id == "test-board"
    
    # Test missing API key
    with pytest.raises(ConfigurationError, match="Trello API key is required"):
        TrelloConfig(
            name="trello",
            url="https://api.trello.com/1",
            api_token="test-token"
        )
        
    # Test missing API token
    with pytest.raises(ConfigurationError, match="Trello API token is required"):
        TrelloConfig(
            name="trello",
            url="https://api.trello.com/1",
            api_key="test-key"
        )

def test_trello_config_from_env():
    """Test creating Trello config from environment variables."""
    os.environ["TRELLO_NAME"] = "trello"
    os.environ["TRELLO_URL"] = "https://api.trello.com/1"
    os.environ["TRELLO_API_KEY"] = "test-key"
    os.environ["TRELLO_API_TOKEN"] = "test-token"
    os.environ["TRELLO_ORGANIZATION_ID"] = "test-org"
    os.environ["TRELLO_BOARD_TEMPLATE_ID"] = "test-board"
    
    config = TrelloConfig.from_env()
    assert config.name == "trello"
    assert config.url == "https://api.trello.com/1"
    assert config.api_key == "test-key"
    assert config.api_token == "test-token"
    assert config.organization_id == "test-org"
    assert config.board_template_id == "test-board"
    
    # Clean up
    del os.environ["TRELLO_NAME"]
    del os.environ["TRELLO_URL"]
    del os.environ["TRELLO_API_KEY"]
    del os.environ["TRELLO_API_TOKEN"]
    del os.environ["TRELLO_ORGANIZATION_ID"]
    del os.environ["TRELLO_BOARD_TEMPLATE_ID"]

def test_config_load():
    """Test loading config from environment."""
    os.environ["TRELLO_NAME"] = "trello"
    os.environ["TRELLO_URL"] = "https://api.trello.com/1"
    os.environ["TRELLO_API_KEY"] = "test-key"
    os.environ["TRELLO_API_TOKEN"] = "test-token"
    
    config = TrelloConfig.from_env()
    assert config.name == "trello"
    assert config.url == "https://api.trello.com/1"
    assert config.api_key == "test-key"
    assert config.api_token == "test-token"
    
    # Clean up
    del os.environ["TRELLO_NAME"]
    del os.environ["TRELLO_URL"]
    del os.environ["TRELLO_API_KEY"]
    del os.environ["TRELLO_API_TOKEN"] 