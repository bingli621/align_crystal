"""YAML files: the only module that knows YAML.

A parameters file holds the nested dict of dict_io.py (its layout is there), of any `Instrument`.
`load(path)` lays a file over the default instrument of the class it names (`from_overrides`;
every file names its `instrument:`), so a file need hold only what differs; `save(instrument,
path)` writes a complete one. `params.yaml` next to this module is the default diffractometer
saved (with an aluminium sample), as a reference of how a parameters file looks.

Files are written as params.yaml is laid out: in the order of the dict, with the innermost lists
and dicts on one line (`at: [0, 0, 1.0]`, `ei: {value: 14.0, unit: meV, comment: incident energy}`).
"""

from pathlib import Path

import yaml

from ..instrument import Instrument
from .dict_io import from_overrides, to_dict

PARAMS_FILE = Path(__file__).parent / "params.yaml"  # the default diffractometer saved: a reference


def read_yaml(path) -> dict:
    """The nested dict stored in the YAML file `path` (empty if the file is)."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_yaml(data: dict, path) -> None:
    """Store the nested dict `data` in the YAML file `path`, in its order, with the innermost
    lists and dicts on one line."""
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None)


def load(path, loader=read_yaml, **kwargs) -> Instrument:
    """The default instrument of the class the file names (see `from_overrides`), made with
    `kwargs` (for the diffractometer: `sample`, `params`), with the parameters file `path` laid
    over it: the file need hold only what differs. It is read with `loader`, a function from a
    path to the nested dict (default: YAML)."""
    return from_overrides(loader(path), **kwargs)


def save(instrument: Instrument, path) -> None:
    """Write the complete parameters file of `instrument` to `path` (YAML), all its components
    included and its class named: `load(path)` gives it back."""
    write_yaml(to_dict(instrument), path)
