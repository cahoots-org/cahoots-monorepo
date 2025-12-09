"""Tech Stack Configuration Loader"""

import os
import yaml
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TechStackConfig:
    """Configuration for a tech stack."""
    name: str
    display_name: str
    description: str

    # Category (backend, frontend, cli, worker, etc.)
    category: str = "backend"

    # Project structure
    src_dir: str = "src"
    test_dir: str = "tests"
    config_files: Dict[str, str] = field(default_factory=dict)

    # Commands
    install_command: str = ""
    test_command: str = ""
    build_command: str = ""
    start_command: str = ""

    # File patterns
    source_pattern: str = ""
    test_pattern: str = ""

    # Conventions for LLM code generation (plain English guidance)
    conventions: str = ""

    # Runner configuration
    runner_image: str = ""


class TechStackLoader:
    """Loads and manages tech stack configurations."""

    def __init__(self):
        self._stacks: Dict[str, TechStackConfig] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all tech stack configurations from YAML files."""
        config_dir = os.path.dirname(__file__)

        for filename in os.listdir(config_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(config_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and 'name' in data:
                            self._stacks[data['name']] = self._parse_config(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

    def _parse_config(self, data: Dict) -> TechStackConfig:
        """Parse YAML data into TechStackConfig."""
        return TechStackConfig(
            name=data.get('name', ''),
            display_name=data.get('display_name', ''),
            description=data.get('description', ''),
            category=data.get('category', 'backend'),
            src_dir=data.get('src_dir', 'src'),
            test_dir=data.get('test_dir', 'tests'),
            config_files=data.get('config_files', {}),
            install_command=data.get('install_command', ''),
            test_command=data.get('test_command', ''),
            build_command=data.get('build_command', ''),
            start_command=data.get('start_command', ''),
            source_pattern=data.get('source_pattern', ''),
            test_pattern=data.get('test_pattern', ''),
            conventions=data.get('conventions', ''),
            runner_image=data.get('runner_image', ''),
        )

    def get(self, name: str) -> Optional[TechStackConfig]:
        """Get a tech stack configuration by name."""
        return self._stacks.get(name)

    def list_all(self) -> list:
        """List all available tech stacks."""
        return [
            {
                'name': stack.name,
                'display_name': stack.display_name,
                'description': stack.description,
                'category': stack.category,
            }
            for stack in self._stacks.values()
        ]

    def reload(self) -> None:
        """Reload all configurations."""
        self._stacks = {}
        self._load_all()


# Global instance
_loader: Optional[TechStackLoader] = None


def get_tech_stack_loader() -> TechStackLoader:
    """Get the global tech stack loader instance."""
    global _loader
    if _loader is None:
        _loader = TechStackLoader()
    return _loader


def get_tech_stack(name: str) -> Optional[TechStackConfig]:
    """Get a tech stack configuration by name."""
    return get_tech_stack_loader().get(name)


def list_tech_stacks() -> list:
    """List all available tech stacks."""
    return get_tech_stack_loader().list_all()
