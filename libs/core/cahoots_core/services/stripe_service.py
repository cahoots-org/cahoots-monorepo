"""Stripe service implementation."""

from typing import Any, Dict, List, Optional

from cahoots_core.utils.config import Config
from cahoots_core.utils.infrastructure.stripe.client import (
    StripeClient,
    get_stripe_client,
)


class StripeService:
    """Service for managing Stripe payments and subscriptions."""

    def __init__(self, config: Config):
        """Initialize Stripe service.

        Args:
            config: Configuration containing Stripe settings
        """
        self.client = get_stripe_client(config.stripe.api_key)
