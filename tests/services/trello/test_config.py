"""Tests for TrelloConfig."""
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from src.services.trello.config import TrelloConfig
from src.utils.exceptions import ConfigurationError

def test_config_init_success() -> None:
    """Test successful config initialization."""
    config = TrelloConfig(
        api_key="test_key",
        api_token="test_token"
    )
    assert config.api_key == "test_key"
    assert config.api_token == "test_token"
    assert config.base_url == "https://api.trello.com/1"
    assert config.timeout == 30
    assert config.retry_attempts == 3
    assert config.retry_delay == 1

def test_config_init_missing_required() -> None:
    """Test config initialization with missing required fields."""
    with pytest.raises(ConfigurationError, match="Invalid service configuration"):
        TrelloConfig()

    with pytest.raises(ConfigurationError, match="Invalid service configuration"):
        TrelloConfig(api_key="test_key")

    with pytest.raises(ConfigurationError, match="Invalid service configuration"):
        TrelloConfig(api_token="test_token")

def test_config_init_empty_values() -> None:
    """Test config initialization with empty values."""
    with pytest.raises(ConfigurationError, match="Trello API key is required"):
        TrelloConfig(api_key="", api_token="test_token")

    with pytest.raises(ConfigurationError, match="Trello API token is required"):
        TrelloConfig(api_key="test_key", api_token="")

def test_config_from_env_success() -> None:
    """Test loading config from environment variables."""
    env_vars = {
        "TRELLO_API_KEY": "env_key",
        "TRELLO_API_TOKEN": "env_token",
        "TRELLO_BASE_URL": "https://custom.trello.com",
        "TRELLO_TIMEOUT": "60"
    }
    
    with patch.dict("os.environ", env_vars, clear=True):
        config = TrelloConfig.from_env()
        assert config.api_key == "env_key"
        assert config.api_token == "env_token"
        assert config.base_url == "https://custom.trello.com"
        assert config.timeout == 60

def test_config_from_env_missing_required() -> None:
    """Test loading config from environment with missing required variables."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ConfigurationError, match="Invalid service configuration"):
            TrelloConfig.from_env()

    with patch.dict("os.environ", {"TRELLO_API_KEY": "env_key"}, clear=True):
        with pytest.raises(ConfigurationError, match="Invalid service configuration"):
            TrelloConfig.from_env()

    with patch.dict("os.environ", {"TRELLO_API_TOKEN": "env_token"}, clear=True):
        with pytest.raises(ConfigurationError, match="Invalid service configuration"):
            TrelloConfig.from_env()

def test_config_optional_fields() -> None:
    """Test config initialization with optional fields."""
    config = TrelloConfig(
        api_key="test_key",
        api_token="test_token",
        organization_id="org_id",
        board_template_id="template_id"
    )
    assert config.organization_id == "org_id"
    assert config.board_template_id == "template_id"

def test_config_validation() -> None:
    """Test config field validation."""
    # Test invalid timeout
    with pytest.raises(ConfigurationError, match="Timeout must be positive"):
        TrelloConfig(
            api_key="test_key",
            api_token="test_token",
            timeout=-1
        )

    # Test invalid retry values
    with pytest.raises(ConfigurationError, match="Retry attempts must be non-negative"):
        TrelloConfig(
            api_key="test_key",
            api_token="test_token",
            retry_attempts=-1
        )

    with pytest.raises(ConfigurationError, match="Retry delay must be positive"):
        TrelloConfig(
            api_key="test_key",
            api_token="test_token",
            retry_delay=-1
        ) 

def test_config_from_env_validation_error() -> None:
    """Test handling of validation error in from_env."""
    # Test with invalid timeout value
    env_vars = {
        "TRELLO_API_KEY": "env_key",
        "TRELLO_API_TOKEN": "env_token",
        "TRELLO_TIMEOUT": "invalid"  # Invalid timeout value - will fail type conversion
    }
    
    with patch.dict("os.environ", env_vars, clear=True):
        with pytest.raises(ConfigurationError, match="Invalid service configuration"):
            TrelloConfig.from_env()

    # Test with invalid retry attempts value
    env_vars = {
        "TRELLO_API_KEY": "env_key",
        "TRELLO_API_TOKEN": "env_token",
        "TRELLO_RETRY_ATTEMPTS": "abc"  # Invalid retry attempts - will fail type conversion
    }
    
    with patch.dict("os.environ", env_vars, clear=True):
        with pytest.raises(ConfigurationError, match="Invalid service configuration"):
            TrelloConfig.from_env() 