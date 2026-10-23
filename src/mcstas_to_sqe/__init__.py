"""mcstas_to_sqe."""

import os
from pathlib import Path

__version__ = "0.1.0"


def default_work_dir() -> Path:
    """Return the folder that generated files go into.

    The folder holds mcstas_input/ (McStas builds), mcstas_output/ (simulation results) and
    output/ (figures), where the user can see them. It is looked up on every call.

    Returns
    -------
    :
        The environment variable ``MCSTAS_TO_SQE_WORKDIR`` (e.g. a scratch disk) if set, else the
        current folder.
    """
    return Path(os.environ.get("MCSTAS_TO_SQE_WORKDIR") or Path.cwd())


def default_figures_dir(work_dir: str | Path | None = None) -> Path:
    """Return the folder for figures and other results made from the simulations.

    The folder holds e.g. gifs and peak lists. It is not created here: whatever saves into it
    creates it.

    Parameters
    ----------
    work_dir:
        Work folder. If ``None``, :func:`default_work_dir` is used.

    Returns
    -------
    :
        ``work_dir/output``.
    """
    return Path(work_dir or default_work_dir()) / "output"
