"""align_crystal."""

import os
from pathlib import Path

__version__ = "0.1.0"

# the project folder (align_crystal/, holding src/): generated files go here, not in the package.
# The environment variable ALIGN_CRYSTAL_ROOT puts them elsewhere (e.g. a scratch disk); it is
# needed unless the package is an editable install of the project folder (as with pixi).
PROJECT_ROOT = Path(os.environ.get("ALIGN_CRYSTAL_ROOT", Path(__file__).resolve().parents[2]))
