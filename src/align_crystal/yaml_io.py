"""YAML files: the only module that knows YAML.

`yaml_loader` is a loader (a function from a path to the nested dict that the entities take, see
`Instrument.from_dict`), and `write_yaml` writes that dict back (`Instrument.to_dict`).
"""

import yaml


def yaml_loader(path) -> dict:
    """The nested dict stored in the YAML file `path`."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_yaml(data: dict, path) -> None:
    """Store the nested dict `data` in the YAML file `path`."""
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)
