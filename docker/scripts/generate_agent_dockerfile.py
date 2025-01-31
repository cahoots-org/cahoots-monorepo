#!/usr/bin/env python3
"""Generate agent-specific Dockerfiles from template."""

import argparse
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

def validate_config(config: Dict[str, Any], agent_name: str) -> None:
    """Validate the agent configuration."""
    required_fields = {
        'event_subscriptions': dict,
        'ai': {
            'provider': str,
            'models': {
                'default': str,
                'fallback': str,
                'embeddings': str
            },
            'settings': {
                'temperature': (int, float),
                'max_tokens': int
            }
        },
        'settings': {
            'log_level': str,
            'metrics_enabled': bool,
            'health_check_interval': int,
            'retry_attempts': int,
            'timeout': int
        }
    }

    def validate_structure(data: Dict[str, Any], schema: Dict[str, Any], path: str = '') -> None:
        for key, expected_type in schema.items():
            current_path = f"{path}.{key}" if path else key
            if key not in data:
                raise ValueError(f"Missing required field: {current_path}")
            
            if isinstance(expected_type, dict):
                if not isinstance(data[key], dict):
                    raise ValueError(f"Field {current_path} must be a dictionary")
                validate_structure(data[key], expected_type, current_path)
            elif isinstance(expected_type, tuple):
                if not isinstance(data[key], expected_type):
                    raise ValueError(f"Field {current_path} must be one of types: {expected_type}")
            elif not isinstance(data[key], expected_type):
                raise ValueError(f"Field {current_path} must be of type {expected_type.__name__}")

    try:
        validate_structure(config, required_fields)
    except ValueError as e:
        print(f"Error in {agent_name} configuration: {e}", file=sys.stderr)
        raise

def load_agent_config(agent_name: str) -> dict:
    """Load agent configuration from yaml file."""
    config_path = Path(f"config/agents/{agent_name}.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Agent config not found: {config_path}")
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise ValueError(f"Invalid configuration format in {config_path}")
            validate_config(config, agent_name)
            return config
    except yaml.YAMLError as e:
        print(f"Error parsing {config_path}: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error loading {config_path}: {e}", file=sys.stderr)
        raise

def generate_dockerfile(agent_name: str, output_dir: str) -> None:
    """Generate a Dockerfile for the specified agent."""
    try:
        # Load agent configuration
        config = load_agent_config(agent_name)
        
        # Read template
        template_path = Path("docker/agents/Dockerfile.template")
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path) as f:
            template = f.read()
        
        # Replace template variables
        dockerfile = template.replace("${AGENT_NAME}", agent_name)
        dockerfile = dockerfile.replace("${AGENT_DESCRIPTION}", config.get('description', ''))
        dockerfile = dockerfile.replace("${AGENT_ROLE}", config.get('role', ''))
        
        # Create output directory if it doesn't exist
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Dockerfile
        dockerfile_path = output_dir / f"{agent_name}.Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(f"""# Generated from Dockerfile.template
# Do not edit directly

{dockerfile}""")
        
        print(f"Generated Dockerfile for agent '{agent_name}' at {dockerfile_path}")
    
    except Exception as e:
        print(f"Error generating Dockerfile for {agent_name}: {e}", file=sys.stderr)
        raise

def main():
    """Parse arguments and generate Dockerfile."""
    parser = argparse.ArgumentParser(description="Generate agent Dockerfiles from template")
    parser.add_argument("agent_name", help="Name of the agent to generate Dockerfile for")
    parser.add_argument("--output-dir", default="docker/agents",
                       help="Output directory for generated Dockerfile")
    
    try:
        args = parser.parse_args()
        generate_dockerfile(args.agent_name, args.output_dir)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 