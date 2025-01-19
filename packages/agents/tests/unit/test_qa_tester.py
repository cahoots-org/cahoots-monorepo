import pytest
from unittest.mock import AsyncMock, Mock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List
import asyncio

from packages.agent_qa import QATester
from src.services.github_service import GitHubService
from src.utils.config import Config, ServiceConfig
from src.utils.base_logger import BaseLogger

// ... existing code ... 