#!/usr/bin/env python3
"""Extract and merge dependencies from pyproject.toml files."""

import glob
import os
from typing import Dict, Set
import tomli

def is_local_package(dep: str) -> bool:
    """Check if a dependency is a local package."""
    return dep.startswith("cahoots-")

def extract_deps(path: str) -> Set[str]:
    """Extract dependencies from a pyproject.toml file."""
    with open(path, "rb") as f:
        try:
            data = tomli.load(f)
            project = data.get("project", {})
            deps = project.get("dependencies", [])
            # Filter out local package dependencies
            return {dep for dep in deps if not is_local_package(dep)}
        except Exception as e:
            print(f"Error processing {path}: {e}")
            return set()

def main():
    """Extract and merge all dependencies."""
    all_deps: Set[str] = set()
    
    # Find all pyproject.toml files
    for toml_file in glob.glob("packages/*/pyproject.toml"):
        deps = extract_deps(toml_file)
        all_deps.update(deps)
    
    # Write merged dependencies
    with open("requirements.txt", "w") as f:
        for dep in sorted(all_deps):
            f.write(f"{dep}\n")

if __name__ == "__main__":
    main() 