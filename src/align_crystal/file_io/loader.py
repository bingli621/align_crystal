"""YAML for the Instrument: the implementation of the `ConfigFormat` that instrument.py defines,
and the convenient `load_config` / `save_config` that inject it."""

import yaml

from ..instrument import Diffractometer, Instrument


class YamlFormat:
    """Implements `align_crystal.instrument.instrument.ConfigFormat` with YAML files."""

    def read(self, path):
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def write(self, data, path):
        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)


YAML = YamlFormat()


def load_config(source=None, cls=Diffractometer, fmt=YAML):
    """An instrument of kind `cls` with its default values and `source` applied on top: a file
    path (read with `fmt`), a dict of overrides or None. An Instrument is returned as is."""
    if isinstance(source, Instrument):
        return source
    if isinstance(source, dict):
        return cls.from_overrides(source, fmt)
    if source:
        return cls.from_file(source, fmt)
    return cls.from_overrides({}, fmt)


def save_config(inst, path, fmt=YAML):
    """Write the (resolved) instrument to `path`, to archive next to the run output."""
    inst.to_file(path, fmt)
