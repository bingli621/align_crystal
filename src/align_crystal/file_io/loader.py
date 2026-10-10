"""Load and save an Instrument as YAML, on top of the default values of its kind."""

import copy

import yaml

from align_crystal.instrument import Diffractometer, Instrument


def _read_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _merge(base, over, roles, path=""):
    """Return `base` with the values of `over` applied, recursively. Unknown keys raise.
    The section of a component (a role) may also set `name`, its McStas instance name."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        if key not in base and not (key == "name" and path.rstrip(".") in roles):
            raise ValueError(f"Unknown config key: {path}{key}")
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            out[key] = _merge(base[key], value, roles, f"{path}{key}.")
        else:
            out[key] = value
    return out


def load_config(source=None, cls=Diffractometer):
    """An instrument of kind `cls` with its default values and `source` applied on top: a YAML
    path, a dict of overrides or None. An Instrument is returned as is."""
    if isinstance(source, Instrument):
        return source
    overrides = (
        source if isinstance(source, dict) else _read_yaml(source) if source else {}
    )
    defaults = _read_yaml(cls.PARAMS_FILE)
    data = _merge(
        defaults, overrides, defaults["placements"]
    )  # roles = the keys of placements
    return cls.from_dict(data)


def save_config(inst, path):
    """Write the (resolved) instrument to YAML, to archive next to the run output."""
    with open(path, "w") as f:
        yaml.safe_dump(inst.to_dict(), f, sort_keys=False)
