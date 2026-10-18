"""The entities: the diffractometer is a set of components (no files, no McStas knowledge; io/ and
mcstas/ are adapters around them and the only ones importing from here).

Generic, for any instrument:
components/        the components, one dataclass each (misc.py, source.py, detector.py, crystal.py)
samples/           the ready-made samples (aluminum, la2ni7), with their CIF files
params.py          InstrParam: one instrument parameter (a McStas instrument parameter)
geometry.py        rotation, place: where the components are in the lab frame, as McStas places them

This instrument:
diffractometer.py  SingleCrystalDiffractometer(sample, ei, omega, chi, phi), the single-crystal
                   diffractometer: makes its own components, each knowing where it sits; params,
                   update_params, instr_params, positions
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
from .diffractometer import SingleCrystalDiffractometer
from .params import InstrParam
from .samples import aluminum, la2ni7

__all__ = [
    "Arm",
    "Component",
    "InstrParam",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "SingleCrystalDiffractometer",
    "Single_crystal",
    "Slit",
    "Source_simple",
    "aluminum",
    "la2ni7",
]
