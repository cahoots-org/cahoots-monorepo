"""Tests for Stripe service."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from cahoots_core.utils.infrastructure import StripeClient

@pytest.fixture
def mock_stripe():
    """Create a mock Stripe client with specific test functionality."""
    mock = MagicMock(spec=StripeClient)
    mock.construct_event = MagicMock()
    mock.handle_webhook_event = AsyncMock()
    mock.create_customer = AsyncMock()
    mock.create_subscription = AsyncMock()
    mock.cancel_subscription = AsyncMock()
    mock.update_subscription = AsyncMock()
    return mock 