"""YAML files: the only module that knows YAML.

`params.yaml` next to it is the default diffractometer saved, as a reference of how a parameters
file looks: `load(file)` lays such a file over the default one, so a file need hold only what
differs (see dict_io.py). `write_yaml(to_dict(d), path)` saves one.
"""

from pathlib import Path

import yaml

from ..instrument import DEFAULT_PARAMS, Params
from .dict_io import over_default

PARAMS_FILE = Path(__file__).parent / "params.yaml"  # the default diffractometer saved: a reference


def yaml_loader(path) -> dict:
    """The nested dict stored in the YAML file `path`."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_yaml(data: dict, path) -> None:
    """Store the nested dict `data` in the YAML file `path`."""
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load(file, sample=None, params: Params = DEFAULT_PARAMS, loader=yaml_loader):
    """The diffractometer made with `sample` and `params` (see
    `SingleCrystalDiffractometer`), with the parameters `file` laid over it, read with `loader` (a
    function from a path to the nested dict; default: YAML)."""
    return over_default(loader(file), sample, params)
