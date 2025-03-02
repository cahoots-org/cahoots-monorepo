"""Initialize tests package and add libs to Python path"""

import os
import sys
from pathlib import Path

# Add the libs directory to Python path
root_dir = Path(__file__).parents[2]  # Go up from tests/features to project root
libs_dir = root_dir / "libs/events"
if libs_dir.exists() and str(libs_dir) not in sys.path:
    sys.path.insert(0, str(libs_dir))
