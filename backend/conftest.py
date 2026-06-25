import os
import sys
from pathlib import Path

# Add the project root (parent directory of 'backend') to sys.path
# so that the 'backend' folder is importable as a module package.
backend_dir = Path(__file__).parent.resolve()
project_root = str(backend_dir.parent)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
