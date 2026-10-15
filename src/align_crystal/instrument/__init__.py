"""The entities: the diffractometer is a set of components (no files, no McStas knowledge; io/ and
mcstas/ are adapters around them and the only ones importing from here).

Generic, for any instrument:
components/        the components, one dataclass each (misc.py, source.py, detector.py, sample.py)
params.py          InstrParam: one instrument parameter (a McStas instrument parameter);
                   CtrlParam: one control parameter, given when the instrument is made
cif/               a plain folder: the CIF files of the ready-made crystals (aluminum, la2ni7)

model/             this instrument, the single-crystal diffractometer:
  diffractometer.py  SingleCrystalDiffractometer(ctrl_params): makes its own components, each
                     knowing where it sits
"""

from .components import (
    Arm,
    Component,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from .components.sample import aluminum, la2ni7
from .model.diffractometer import SingleCrystalDiffractometer
from .params import CtrlParam, InstrParam, complete_values, with_values

__all__ = [
    "Arm",
    "Component",
    "CtrlParam",
    "InstrParam",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "SingleCrystalDiffractometer",
    "Single_crystal",
    "Slit",
    "Source_simple",
    "aluminum",
    "complete_values",
    "la2ni7",
    "with_values",
]
