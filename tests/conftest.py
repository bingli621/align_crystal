import pytest

from instruments import SingleCrystalDiffractometer
from align_crystal.yaml_io import yaml_loader


def _update(base, changes):
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _update(base[key], value)
        else:
            base[key] = value
    return base


@pytest.fixture
def diffractometer():
    """diffractometer(changes=None) -> the SingleCrystalDiffractometer of its default parameters
    (the YAML file next to the class) with the nested dict `changes` applied."""

    def make(changes=None):
        data = _update(yaml_loader(SingleCrystalDiffractometer.PARAMS_FILE), changes or {})
        return SingleCrystalDiffractometer.from_dict(data)

    return make
