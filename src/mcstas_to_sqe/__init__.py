"""mcstas_to_sqe."""

import os
from pathlib import Path

__version__ = "0.1.0"


def default_work_dir():
    """The folder the generated files go into, for the user to see: mcstas_input/ (McStas
    builds), mcstas_output/ (simulation results) and output/ (figures). The environment variable
    MCSTAS_TO_SQE_WORKDIR (e.g. a scratch disk), else the current folder, looked up at each call."""
    return Path(os.environ.get("MCSTAS_TO_SQE_WORKDIR") or Path.cwd())


def default_figures_dir(work_dir=None):
    """The folder of the figures and other results made from the simulations (gifs, peak
    lists): `work_dir/output` (None for `default_work_dir()`). Created by whatever saves there."""
    return Path(work_dir or default_work_dir()) / "output"
