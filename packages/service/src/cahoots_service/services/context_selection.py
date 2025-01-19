"""Context selection service for LLM request enrichment."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID
from fnmatch import fnmatch
import json
from json_rules_engine import Engine, Rule
from pathlib import Path

from sqlalchemy.orm import Session
from packages.service.src.ai_dev_team_service.core.dependencies import BaseDeps
from cahoots_context.storage.context_service import ContextEventService

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
        return (channel in self.channels or "*" in self.channels) and \
               (capability in self.capabilities or "*" in self.capabilities)

class ContextChannel:
    """Represents a channel for context selection"""
    def __init__(self, config: Dict):
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 0)
        self.rules = config.get("rules", [])
        self.events = set(config.get("events", []))
        self.max_items = config.get("max_items", 50)
        self.required_capabilities = set(config.get("required_capabilities", []))
        
    def accepts_event(self, event_type: str) -> bool:
        """Check if channel accepts an event type"""
        return event_type in self.events or "*" in self.events

class ContextRuleEngine:
    """Rules engine for context selection using json-rules-engine"""
    
    def __init__(self, rules_path: str = "config/rules"):
        self.engine = Engine()
        self.rules_path = Path(rules_path)
        self.channels: Dict[str, ContextChannel] = {}
        self.agents: Dict[str, ContextAgent] = {}
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
                    for rule in rules:
                        self.engine.add_rule(Rule(rule))
    
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
                    "rules": ["security_rules.json"]
                },
                {
                    "name": "performance_analyst",
                    "enabled": True,
                    "capabilities": ["performance_analysis", "optimization"],
                    "channels": ["architectural_decisions", "requirements"],
                    "priority": 90,
                    "memory_size": 1500,
                    "context_window": 3000,
                    "rules": ["performance_rules.json"]
                },
                {
                    "name": "code_reviewer",
                    "enabled": True,
                    "capabilities": ["code_review", "pattern_matching"],
                    "channels": ["*"],
                    "priority": 80,
                    "memory_size": 1000,
                    "context_window": 2000,
                    "rules": ["code_review_rules.json"]
                }
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
                    "required_capabilities": ["security_analysis", "performance_analysis"]
                },
                {
                    "name": "requirements",
                    "enabled": True,
                    "priority": 90,
                    "events": ["*"],
                    "max_items": 20,
                    "rules": ["requirements_rules.json"],
                    "required_capabilities": []
                },
                {
                    "name": "discussions",
                    "enabled": True,
                    "priority": 80,
                    "events": ["code_review", "security_review"],
                    "max_items": 15,
                    "rules": ["discussion_rules.json"],
                    "required_capabilities": ["code_review"]
                }
            ]
        }
        
        with open(self.rules_path / "channels.json", "w") as f:
            json.dump(channels_config, f, indent=2)
            
        # Create default architectural rules
        architectural_rules = {
            "filters": [{
                "name": "approved_only",
                "conditions": {
                    "all": [{
                        "fact": "status",
                        "operator": "equal",
                        "value": "approved"
                    }]
                }
            }],
            "scoring": [
                {
                    "name": "priority_high",
                    "conditions": {
                        "all": [{
                            "fact": "priority",
                            "operator": "equal",
                            "value": "high"
                        }]
                    },
                    "score": 800
                },
                {
                    "name": "recency_30d",
                    "conditions": {
                        "all": [{
                            "fact": "age_days",
                            "operator": "lessThanInclusive",
                            "value": 30
                        }]
                    },
                    "score": 600
                },
                {
                    "name": "impact_security",
                    "conditions": {
                        "all": [{
                            "fact": "impact",
                            "operator": "contains",
                            "value": "security"
                        }]
                    },
                    "score": 1000
                }
            ]
        }
        
        with open(self.rules_path / "architectural_rules.json", "w") as f:
            json.dump(architectural_rules, f, indent=2)

class ContextSelectionService:
    def __init__(self, deps: BaseDeps):
        self.db = deps.db
        self.context_service = deps.context_service
        self.rule_engine = ContextRuleEngine()
    
    async def get_llm_context(
        self,
        project_id: UUID,
        request_type: str,
        relevant_files: Optional[List[str]] = None,
        max_context_items: int = 50,
        required_capabilities: Optional[List[str]] = None
    ) -> Dict:
        """Get relevant context for an LLM request."""
        # Get full project context
        full_context = await self.context_service.get_context(project_id)
        if not full_context:
            return {}
            
        selected_context = {}
        
        # Get available agents with required capabilities
        available_agents = []
        if required_capabilities:
            for agent in self.rule_engine.agents.values():
                if agent.enabled and all(cap in agent.capabilities for cap in required_capabilities):
                    available_agents.append(agent)
        else:
            available_agents = [a for a in self.rule_engine.agents.values() if a.enabled]
            
        # Sort agents by priority
        available_agents.sort(key=lambda x: x.priority, reverse=True)
        
        # Process each enabled channel with available agents
        channels = sorted(
            [c for c in self.rule_engine.channels.values() if c.enabled],
            key=lambda x: x.priority,
            reverse=True
        )
        
        for channel in channels:
            if not channel.accepts_event(request_type):
                continue
                
            if channel.name not in full_context:
                continue
                
            # Check if we have agents with required capabilities
            channel_agents = [
                a for a in available_agents 
                if all(cap in a.capabilities for cap in channel.required_capabilities)
            ]
            
            if channel.required_capabilities and not channel_agents:
                continue
                
            content = full_context[channel.name]
            
            # Apply channel-specific filtering with available agents
            if channel.name == "architectural_decisions":
                filtered = self._filter_architectural_decisions(content, request_type)
                selected_context[channel.name] = filtered[:channel.max_items]
            elif channel.name == "requirements":
                filtered = self._filter_requirements(content, request_type, relevant_files)
                selected_context[channel.name] = filtered
                
        return selected_context

    def _filter_architectural_decisions(
        self,
        decisions: List[Dict],
        request_type: str
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
                    now - datetime.fromisoformat(
                        decision.get("timestamp", now.isoformat()).replace("Z", "+00:00")
                    )
                ).days
            }
            
            # Run rules engine
            result = self.rule_engine.engine.run(facts)
            
            if result.success:
                score = 1000  # Base score
                for action in result.actions:
                    if "score" in action:
                        score += action["score"]
                
                decision["_score"] = score
                filtered.append(decision)

        # Sort by score and limit results for specific review types
        sorted_decisions = sorted(
            filtered, 
            key=lambda x: (-x["_score"], x.get("title", ""))
        )
        
        if request_type in ["security_review", "performance_review"]:
            category = request_type.split("_")[0]
            return [
                d for d in sorted_decisions 
                if category in d.get("impact", [])
            ][:2]
            
        return sorted_decisions

    def _filter_requirements(
        self,
        requirements: Dict[str, Dict],
        request_type: str,
        relevant_files: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """Filter requirements based on request type and file patterns."""
        if not requirements or not isinstance(requirements, dict):
            return {}
            
        filtered = {}
        request_category = request_type.split('_')[0] if request_type and '_' in request_type else request_type

        # Handle special sections first
        if "valid_section" in requirements and isinstance(requirements["valid_section"], dict):
            filtered["valid_section"] = requirements["valid_section"]
            return filtered

        # Handle direct category requirements
        if request_type in ['security_review', 'performance_review']:
            for category in ['performance', 'security']:
                if category in requirements:
                    value = requirements[category]
                    if isinstance(value, (dict, list)):
                        filtered[category] = value
        else:
            if request_category in requirements:
                value = requirements[request_category]
                if isinstance(value, (dict, list)):
                    filtered[request_category] = value

        # Handle functional requirements
        if 'functional' in requirements and isinstance(requirements['functional'], list):
            functional_reqs = []
            for req in requirements['functional']:
                if not isinstance(req, dict):
                    continue

                # Check file relevance if files specified
                if relevant_files and req.get('related_files'):
                    matches = False
                    for pattern in req['related_files']:
                        if any(fnmatch(file, pattern) for file in relevant_files):
                            matches = True
                            break
                    if not matches:
                        continue
                elif relevant_files and not req.get('related_files', []):
                    continue

                # Check tag relevance
                tags = req.get('tags', [])
                if request_category and request_category != 'all':
                    if request_category not in tags:
                        continue

                functional_reqs.append(req)

            filtered['functional'] = functional_reqs

        return filtered 