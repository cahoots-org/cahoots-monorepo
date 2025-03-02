"""Agent factory for creating different types of agents."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Type

import yaml

from cahoots_core.ai import AIProvider
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus import EventSystem

from .base import BaseAgent
from .developer.core.developer import Developer
from .pm.project_manager import ProjectManager
from .qa.qa_tester import QATester
from .ux.core.ux_designer import UXDesigner


class AgentFactory:
    """Factory for creating agent instances."""

    _agent_types: Dict[str, Type[BaseAgent]] = {
        "developer": Developer,
        "qa_tester": QATester,
        "ux_designer": UXDesigner,
        "project_manager": ProjectManager,
    }

    @classmethod
    def load_event_subscriptions(cls, agent_type: str) -> Dict[str, str]:
        """Load event subscriptions from config file.

        Args:
            agent_type: Type of agent to load subscriptions for

        Returns:
            Dict mapping event types to handler names
        """
        # Try environment variable first
        config_path = os.getenv("AGENT_CONFIG_PATH", "config/agents")

        # Look for agent-specific config first, then fall back to default
        paths = [Path(config_path) / f"{agent_type}.yaml", Path(config_path) / "default.yaml"]

        for path in paths:
            if path.exists():
                with open(path) as f:
                    config = yaml.safe_load(f)
                    return config.get("event_subscriptions", {})

        return {}  # Return empty dict if no config found

    @classmethod
    def create(
        cls,
        agent_type: str,
        event_system: Optional[EventSystem] = None,
        github_service: Optional[GitHubService] = None,
        config: Optional[Dict[str, Any]] = None,
        ai_provider: Optional[AIProvider] = None,
        **kwargs: Any,
    ) -> BaseAgent:
        """Create an agent instance.

        Args:
            agent_type: Type of agent to create
            event_system: Optional event system
            github_service: Optional GitHub service
            config: Optional configuration
            ai_provider: Optional AI provider
            **kwargs: Additional agent-specific arguments

        Returns:
            BaseAgent: Created agent instance

        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in cls._agent_types:
            raise ValueError(f"Unsupported agent type: {agent_type}")

        agent_class = cls._agent_types[agent_type]

        # Load event subscriptions from config file
        event_subscriptions = cls.load_event_subscriptions(agent_type)

        # Prepare configuration
        config = config or {}
        agent_config = config.setdefault("agents", {}).setdefault(agent_type, {})
        agent_config["event_subscriptions"] = event_subscriptions

        # Prepare constructor arguments
        agent_args = {
            "event_system": event_system,
            "github_service": github_service,
            "config": config,
            "ai_provider": ai_provider,
            **kwargs,
        }

        # Remove None values and arguments not accepted by the constructor
        agent_args = {
            k: v
            for k, v in agent_args.items()
            if v is not None and k in agent_class.__init__.__code__.co_varnames
        }

        return agent_class(**agent_args)
