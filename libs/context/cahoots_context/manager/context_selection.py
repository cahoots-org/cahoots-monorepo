"""Context selection service."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from business_rules.actions import BaseActions, rule_action
from business_rules.engine import run_all
from business_rules.fields import FIELD_NUMERIC, FIELD_TEXT
from business_rules.variables import (
    BaseVariables,
    numeric_rule_variable,
    string_rule_variable,
)

from cahoots_context.storage.context_service import ContextEventService


class ContextVariables(BaseVariables):
    """Variables for context selection rules."""

    def __init__(self, facts: Dict):
        self.facts = facts

    @string_rule_variable
    def status(self):
        """Get status from facts."""
        return self.facts.get("status")

    @string_rule_variable
    def request_type(self):
        """Get request type from facts."""
        return self.facts.get("request_type")

    @string_rule_variable
    def impact(self):
        """Get impact from facts."""
        return self.facts.get("impact")

    @numeric_rule_variable
    def age_days(self):
        """Get age in days from facts."""
        return self.facts.get("age_days", 0)

    @string_rule_variable
    def priority(self):
        """Get priority from facts."""
        return self.facts.get("priority")


class ContextActions(BaseActions):
    """Actions for context selection rules."""

    def __init__(self):
        self.score = 0

    @rule_action(params={"points": FIELD_NUMERIC})
    def add_score(self, points):
        """Add points to the score."""
        self.score += points

    def get_score(self) -> int:
        """Get the current score."""
        return self.score

    def get_results(self) -> Dict:
        """Get the results of rule execution."""
        return {"success": True, "score": self.score}


class ContextAgent:
    """Represents an agent that processes context"""

    def __init__(self, config: Dict):
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.capabilities = set(config.get("capabilities", []))
        self.channels = set(config.get("channels", ["*"]))
        self.rules = config.get("rules", [])
        self.priority = config.get("priority", 0)
        self.max_items = config.get("max_items", 50)
        self.memory_size = config.get("memory_size", 1000)
        self.context_window = config.get("context_window", 2000)

    def can_handle(self, channel: str, capability: str) -> bool:
        """Check if agent can handle a channel and capability"""
        return (channel in self.channels or "*" in self.channels) and (
            capability in self.capabilities or "*" in self.capabilities
        )


class ContextChannel:
    """Represents a context channel"""

    def __init__(self, config: Dict):
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 0)
        self.events = set(config.get("events", ["*"]))
        self.max_items = config.get("max_items", 50)
        self.rules = config.get("rules", [])
        self.required_capabilities = set(config.get("required_capabilities", []))


class ContextRuleEngine:
    """Rules engine for context selection using business-rules"""

    def __init__(self, rules_path: str = "config/rules"):
        self.rules_path = Path(rules_path)
        self.channels: Dict[str, ContextChannel] = {}
        self.agents: Dict[str, ContextAgent] = {}
        self.rules = []
        self.load_config()

    def load_config(self):
        """Load rules and configuration"""
        if not self.rules_path.exists():
            self.rules_path.mkdir(parents=True)
            self._create_default_config()

        # Load channels first
        channels_file = self.rules_path / "channels.json"
        if channels_file.exists():
            with open(channels_file) as f:
                channels_config = json.load(f)
                for channel_config in channels_config["channels"]:
                    channel = ContextChannel(channel_config)
                    self.channels[channel.name] = channel

        # Load agents
        agents_file = self.rules_path / "agents.json"
        if agents_file.exists():
            with open(agents_file) as f:
                agents_config = json.load(f)
                for agent_config in agents_config["agents"]:
                    agent = ContextAgent(agent_config)
                    self.agents[agent.name] = agent

        # Load rules for each channel and agent
        for rule_file in self.rules_path.glob("*.json"):
            if rule_file.name not in ["channels.json", "agents.json"]:
                with open(rule_file) as f:
                    rules = json.load(f)
                    self.rules.extend(rules)

    def run(self, facts: Dict) -> Dict:
        """Run rules engine with facts."""
        variables = ContextVariables(facts)
        actions = ContextActions()
        run_all(
            rule_list=self.rules,
            defined_variables=variables,
            defined_actions=actions,
            stop_on_first_trigger=False,
        )
        return actions.get_results()

    def _create_default_config(self):
        """Create default configuration if none exists"""
        # Create default agents
        agents_config = {
            "agents": [
                {
                    "name": "security_expert",
                    "enabled": True,
                    "capabilities": ["security_analysis", "vulnerability_detection"],
                    "channels": ["architectural_decisions", "requirements"],
                    "priority": 100,
                    "memory_size": 2000,
                    "context_window": 4000,
                    "rules": ["security_rules.json"],
                },
                {
                    "name": "performance_analyst",
                    "enabled": True,
                    "capabilities": ["performance_analysis", "optimization"],
                    "channels": ["architectural_decisions", "requirements"],
                    "priority": 90,
                    "memory_size": 1500,
                    "context_window": 3000,
                    "rules": ["performance_rules.json"],
                },
                {
                    "name": "code_reviewer",
                    "enabled": True,
                    "capabilities": ["code_review", "pattern_matching"],
                    "channels": ["*"],
                    "priority": 80,
                    "memory_size": 1000,
                    "context_window": 2000,
                    "rules": ["code_review_rules.json"],
                },
            ]
        }

        with open(self.rules_path / "agents.json", "w") as f:
            json.dump(agents_config, f, indent=2)

        # Create default channels config
        channels_config = {
            "channels": [
                {
                    "name": "architectural_decisions",
                    "enabled": True,
                    "priority": 100,
                    "events": ["security_review", "performance_review", "architectural_decision"],
                    "max_items": 10,
                    "rules": ["architectural_rules.json"],
                    "required_capabilities": ["security_analysis", "performance_analysis"],
                },
                {
                    "name": "requirements",
                    "enabled": True,
                    "priority": 90,
                    "events": ["*"],
                    "max_items": 20,
                    "rules": ["requirements_rules.json"],
                    "required_capabilities": [],
                },
                {
                    "name": "discussions",
                    "enabled": True,
                    "priority": 80,
                    "events": ["code_review", "security_review"],
                    "max_items": 15,
                    "rules": ["discussion_rules.json"],
                    "required_capabilities": ["code_review"],
                },
            ]
        }

        with open(self.rules_path / "channels.json", "w") as f:
            json.dump(channels_config, f, indent=2)

        # Create default architectural rules
        architectural_rules = [
            {
                "conditions": {
                    "all": [{"name": "status", "operator": "equal_to", "value": "approved"}]
                },
                "actions": [{"name": "add_score", "params": {"points": 1000}}],
            },
            {
                "conditions": {
                    "all": [{"name": "priority", "operator": "equal_to", "value": "high"}]
                },
                "actions": [{"name": "add_score", "params": {"points": 800}}],
            },
            {
                "conditions": {
                    "all": [{"name": "age_days", "operator": "less_than_or_equal_to", "value": 30}]
                },
                "actions": [{"name": "add_score", "params": {"points": 600}}],
            },
            {
                "conditions": {
                    "all": [{"name": "impact", "operator": "contains", "value": "security"}]
                },
                "actions": [{"name": "add_score", "params": {"points": 1000}}],
            },
        ]

        with open(self.rules_path / "architectural_rules.json", "w") as f:
            json.dump(architectural_rules, f, indent=2)


class ContextSelectionService:
    """Service for selecting and managing context."""

    def __init__(self):
        self.rule_engine = ContextRuleEngine()
        self.context_service = ContextEventService()

    def _filter_architectural_decisions(
        self, decisions: List[Dict], request_type: str
    ) -> List[Dict]:
        """Filter and score architectural decisions using rules engine."""
        if not decisions or not isinstance(decisions, list):
            return []

        filtered = []
        now = datetime.utcnow()

        for decision in decisions:
            if not isinstance(decision, dict):
                continue

            # Prepare facts for rules engine
            facts = {
                **decision,
                "request_type": request_type,
                "age_days": (
                    now
                    - datetime.fromisoformat(
                        decision.get("timestamp", now.isoformat()).replace("Z", "+00:00")
                    )
                ).days,
            }

            # Run rules engine
            result = self.rule_engine.run(facts)

            if result["success"]:
                decision["_score"] = result["score"]
                filtered.append(decision)

        return filtered
