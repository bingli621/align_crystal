import copy

import pytest

from align_crystal.instruments import SingleCrystalDiffractometer
from align_crystal.io import from_dict, to_dict
from align_crystal.samples import aluminum


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
    (with the aluminium sample) with the nested dict `changes` applied (a null replaces the
    value)."""
    default = to_dict(SingleCrystalDiffractometer(aluminum(at=[0, 0, 0], relative="gonio_phi")))

    def make(changes=None):
        data = _update(copy.deepcopy(default), changes or {})
        return from_dict(data)

    return make
