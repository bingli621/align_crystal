"""YAML parameters files; the only module that knows YAML.

A parameters file holds the nested dict of :mod:`.dict_io` (whose docstring shows the layout),
for any :class:`.Instrument`.

- :func:`load` lays a file over the default instrument of the class it names, so a file need
  only hold what differs. Every file must name its ``instrument:``.
- :func:`save` writes a complete file.

Each instrument keeps its default saved as a reference of how a parameters file looks; for the
diffractometer, instruments/diffractometer/params.yaml (``PARAMS_FILE``).

Files are written in the order of the dict, with the innermost lists and dicts on one line
(``at: [0, 0, 1.0]``, ``ei: {value: 14.0, unit: meV, comment: incident energy}``).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from mcstas_to_sqe.core import Instrument

from .dict_io import from_overrides, to_dict


def read_yaml(path: str | Path) -> dict:
    """Read a nested dict from a YAML file.

    Parameters
    ----------
    path:
        The YAML file.

    Returns
    -------
    :
        The dict, empty if the file is empty.
    """
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_yaml(data: dict, path: str | Path) -> None:
    """Write a nested dict to a YAML file.

    Keys keep their order, and the innermost lists and dicts are written on one line.

    Parameters
    ----------
    data:
        The dict.
    path:
        The YAML file, overwritten if it exists.
    """
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None)


def load(
    path: str | Path, loader: Callable[[str | Path], dict] = read_yaml, **kwargs: Any
) -> Instrument:
    """Load an instrument from a parameters file.

    The file is laid over the default instrument of the class it names (see
    :func:`.from_overrides`), so it need only hold what differs.

    Parameters
    ----------
    path:
        The parameters file.
    loader:
        Reads ``path`` into the nested dict. Default: YAML.
    **kwargs:
        Passed to the class to create the default instrument; for the diffractometer,
        ``sample`` and ``params``.

    Returns
    -------
    :
        The instrument.

    Raises
    ------
    ValueError
        As :func:`.from_dict`.
    """
    return from_overrides(loader(path), **kwargs)


def save(instrument: Instrument, path: str | Path) -> None:
    """Save the complete parameters file of an instrument, as YAML.

    The file names the class and includes all components, so :func:`load` gives the instrument
    back.

    Parameters
    ----------
    instrument:
        The instrument.
    path:
        The file, overwritten if it exists.
    """
    write_yaml(to_dict(instrument), path)
