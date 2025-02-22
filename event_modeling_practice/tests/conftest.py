import os
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def pytest_bdd_apply_tag(tag, function):
    """Register tags for pytest-bdd."""
    return None  # No custom tags needed yet 