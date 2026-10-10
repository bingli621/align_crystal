"""Load and save a DiffractometerConfig as YAML (the defaults are in params.yaml)."""

import copy
from dataclasses import asdict
from pathlib import Path
from typing import get_type_hints

import yaml

from align_crystal.instrument.instrument import Component, DiffractometerConfig, Placement

DEFAULT_CONFIG_PATH = Path(__file__).parent / "params.yaml"


def _read_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _merge(base, over, path=""):
    """Return `base` with the values of `over` applied, recursively. Unknown keys raise."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        # components may override their instance name, which defaults to their key
        if key not in base and not (key == "name" and "component_name" in base):
            raise ValueError(f"Unknown config key: {path}{key}")
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            out[key] = _merge(base[key], value, f"{path}{key}.")
        else:
            out[key] = value
    return out


def from_dict(data):
    """Build a DiffractometerConfig from a complete nested dict."""
    kwargs = {"name": data["name"]}
    for role, cls in get_type_hints(DiffractometerConfig).items():
        if issubclass(cls, Component):  # every component section, typed by its annotation
            kwargs[role] = cls(**data[role])
    kwargs["placements"] = {r: Placement(**p) for r, p in data["placements"].items()}
    return DiffractometerConfig(**kwargs)


def load_config(source=None):
    """The default config with `source` applied on top: a YAML path, a dict of overrides or None.
    A DiffractometerConfig is returned as is."""
    if isinstance(source, DiffractometerConfig):
        return source
    overrides = source if isinstance(source, dict) else _read_yaml(source) if source else {}
    return from_dict(_merge(_read_yaml(DEFAULT_CONFIG_PATH), overrides))


def save_config(cfg, path):
    """Write the (resolved) config to YAML, to archive next to the run output."""
    with open(path, "w") as f:
        yaml.safe_dump(asdict(cfg), f, sort_keys=False)
