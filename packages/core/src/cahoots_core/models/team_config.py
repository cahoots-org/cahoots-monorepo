"""Team configuration models."""
from typing import Dict, Optional, List, Any
from pydantic import BaseModel
import json
from pathlib import Path
import glob
import os

class AgentConfig(BaseModel):
    """Base configuration for any agent type"""
    name: str
    type: str
    model_name: str
    events: Dict[str, List[str]]
    capabilities: Dict[str, Any] = {}
    required_env_vars: Optional[List[str]] = None

class TeamDynamics(BaseModel):
    """Configuration for team collaboration patterns"""
    collaboration_patterns: Dict[str, Dict[str, List[str]]]
    communication_channels: Dict[str, List[str]]

class TeamConfig(BaseModel):
    """Configuration for the AI development team"""
    project_id: str
    agents: Dict[str, AgentConfig]
    team_dynamics: Optional[TeamDynamics] = None
    
    @classmethod
    def load_from_directory(cls, config_dir: str = "config/agents") -> "TeamConfig":
        """Load team configuration from a directory of agent configs"""
        config_path = Path(config_dir)
        if not config_path.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")
            
        # Load all agent configs
        agents = {}
        for agent_file in glob.glob(str(config_path / "*.json")):
            with open(agent_file) as f:
                agent_config = json.load(f)
                agent_id = Path(agent_file).stem  # Use filename without extension as ID
                try:
                    agents[agent_id] = AgentConfig(**agent_config)
                except Exception as e:
                    print(f"Warning: Invalid agent config in {agent_file}: {e}")
        
        # Load team dynamics if exists
        dynamics_path = config_path.parent / "team_dynamics.json"
        team_dynamics = None
        if dynamics_path.exists():
            with open(dynamics_path) as f:
                dynamics_config = json.load(f)
                team_dynamics = TeamDynamics(**dynamics_config)
                
        return cls(
            project_id=os.getenv("PROJECT_ID", "default"),
            agents=agents,
            team_dynamics=team_dynamics
        )
        
    def get_agent_by_type(self, agent_type: str) -> Optional[AgentConfig]:
        """Get the first agent config of a specific type"""
        for agent in self.agents.values():
            if agent.type == agent_type:
                return agent
        return None
        
    def get_agents_by_type(self, agent_type: str) -> List[AgentConfig]:
        """Get all agent configs of a specific type"""
        return [agent for agent in self.agents.values() if agent.type == agent_type]
        
    def get_agents_by_capability(self, capability: str) -> List[AgentConfig]:
        """Get all agents that have a specific capability"""
        return [
            agent for agent in self.agents.values() 
            if capability in agent.capabilities
        ] 