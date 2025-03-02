"""Base agent implementation."""

import logging
from collections.abc import AsyncIterator
from typing import Any, Callable, Dict, List, Optional, Union

from cahoots_core.ai import AIProvider, AIProviderFactory
from cahoots_events.bus import EventSystem


class BaseAgent:
    """Base class for all agents."""

    def __init__(
        self,
        agent_type: str,
        config: Dict[str, Any],
        event_system: Optional[EventSystem] = None,
        ai_provider: Optional[AIProvider] = None,
    ):
        """Initialize the agent.

        Args:
            agent_type: Type of agent (qa_tester, developer, etc)
            config: Agent configuration
            event_system: Optional event system
            ai_provider: Optional AI provider (will be created from config if not provided)
        """
        self.agent_type = agent_type
        self.config = config
        self.event_system = event_system
        self.logger = logging.getLogger(f"agent.{agent_type}")

        # Initialize AI provider
        ai_config = config.get("ai", {})
        self.ai = ai_provider or AIProviderFactory.create(
            provider=ai_config.get("provider", "openai"),
            api_key=ai_config.get("api_key"),
            model=ai_config.get("models", {}).get("default"),
            **ai_config.get("settings", {}),
        )

        # Get agent-specific settings
        agent_config = config.get("agents", {}).get(agent_type, {})
        self.model = agent_config.get("model") or ai_config.get("models", {}).get("default")
        self.temperature = agent_config.get("temperature") or ai_config.get("settings", {}).get(
            "temperature", 0.7
        )

        # Store event subscriptions
        self.event_subscriptions = agent_config.get("event_subscriptions", {})

    async def setup_events(self) -> None:
        """Set up event subscriptions from config."""
        if not self.event_system:
            return

        await self.event_system.connect()

        # Subscribe to configured events
        for event_type, handler_name in self.event_subscriptions.items():
            handler = getattr(self, handler_name, None)
            if handler and callable(handler):
                await self.event_system.subscribe(event_type, handler)
                self.logger.info(f"Subscribed to {event_type} with handler {handler_name}")
            else:
                self.logger.warning(f"Handler {handler_name} not found for event {event_type}")

    async def start(self) -> None:
        """Start the agent."""
        await self.setup_events()
        self.logger.info(f"Agent {self.agent_type} started successfully")

    async def generate_response(
        self, prompt: str, *, temperature: Optional[float] = None, **kwargs: Any
    ) -> str:
        """Generate a response using the AI provider.

        Args:
            prompt: Input prompt
            temperature: Optional override for temperature
            **kwargs: Additional provider-specific args

        Returns:
            str: Generated response
        """
        try:
            return await self.ai.generate_response(
                prompt, temperature=temperature or self.temperature, model=self.model, **kwargs
            )
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            # Try fallback model if configured
            fallback_model = self.config.get("ai", {}).get("models", {}).get("fallback")
            if fallback_model and fallback_model != self.model:
                self.logger.info(f"Retrying with fallback model: {fallback_model}")
                return await self.ai.generate_response(
                    prompt,
                    temperature=temperature or self.temperature,
                    model=fallback_model,
                    **kwargs,
                )
            raise

    async def generate_embeddings(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate embeddings using the AI provider.

        Args:
            texts: List of texts to embed
            **kwargs: Additional provider-specific args

        Returns:
            List[List[float]]: Embedding vectors
        """
        embedding_model = self.config.get("ai", {}).get("models", {}).get("embeddings")
        return await self.ai.generate_embeddings(texts, model=embedding_model, **kwargs)

    async def stream_response(
        self, prompt: str, *, temperature: Optional[float] = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream a response using the AI provider.

        Args:
            prompt: Input prompt
            temperature: Optional override for temperature
            **kwargs: Additional provider-specific args

        Yields:
            str: Response chunks
        """
        async for chunk in self.ai.stream_response(
            prompt, temperature=temperature or self.temperature, model=self.model, **kwargs
        ):
            yield chunk
