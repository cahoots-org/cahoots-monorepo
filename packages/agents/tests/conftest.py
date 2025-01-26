"""Test configuration and fixtures."""
import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Store original env vars
    original_env = {}
    env_vars = {
        "OPENAI_API_KEY": "test-key",
        "ANTHROPIC_API_KEY": "test-key",
        "GITHUB_TOKEN": "test-token",
        "WORKSPACE_DIR": "/tmp/test-workspace"
    }
    
    # Set test env vars
    for key, value in env_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
        
    yield
    
    # Restore original env vars
    for key in env_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key] 