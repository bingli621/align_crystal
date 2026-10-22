"""mcstas_to_sqe."""

import os
from pathlib import Path

__version__ = "0.1.0"


def default_work_dir():
    """The folder the generated files go into, for the user to see: mcstas_input/ (McStas
    builds) and mcstas_output/ (simulation results). The environment variable
    MCSTAS_TO_SQE_WORKDIR (e.g. a scratch disk), else the current folder, looked up at each call."""
    return Path(os.environ.get("MCSTAS_TO_SQE_WORKDIR") or Path.cwd())
