"""Test configuration and fixtures."""
import asyncio
import os
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, Mock, create_autospec, patch
import pytest
import pytest_asyncio
from redis.asyncio import Redis
import json
import httpx
import logging

from src.utils.event_system import EventSystem
from src.utils.task_manager import TaskManager
from src.utils.base_logger import BaseLogger
from src.utils.model import Model
from src.services.task_management.mock import MockTaskManagementService
from src.services.github_service import GitHubService

@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests and handle cleanup."""
    # Store original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    
    yield
    
    # Restore original handlers and close any that were added
    current_handlers = root_logger.handlers[:]
    for handler in current_handlers:
        if handler not in original_handlers:
            handler.close()
            root_logger.removeHandler(handler)

@pytest.fixture
def mock_model():
    """Create a mock model."""
    return AsyncMock()

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create a mock logger."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    return logger

@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    return AsyncMock()

@pytest.fixture
def mock_task_manager():
    """Create a mock task manager."""
    return AsyncMock()

pytest.mark.asyncio(scope="function")