import copy

import pytest

from align_crystal.instrument import (
    CtrlParam,
    SingleCrystalDiffractometer,
    aluminum,
)
from align_crystal.io import from_dict, to_dict


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
    (with the aluminium sample) with the nested dict `changes` applied: a value null is set to
    null, so it is checked."""
    default = to_dict(
        SingleCrystalDiffractometer(
            [
                CtrlParam("crystal", aluminum(at=[0, 0, 0], relative="gonio_phi")),
                CtrlParam("ei", 14),
            ]
        )
    )

    def make(changes=None):
        data = _update(copy.deepcopy(default), changes or {})
        return from_dict(data)

    return make
