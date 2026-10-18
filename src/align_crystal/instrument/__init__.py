"""The entities: the diffractometer is a set of components (no files, no McStas knowledge; io/ and
mcstas/ are adapters around them and the only ones importing from here).

Generic, for any instrument:
components/        the components, one dataclass each (misc.py, source.py, detector.py, crystal.py)
samples/           the ready-made samples (aluminum, la2ni7), with their CIF files
params.py          InstrParam: one instrument parameter (a McStas instrument parameter)
geometry.py        rotation, place: where the components are in the lab frame, as McStas places them
utils.py           evaluate: the number a McStas expression of instrument parameters stands for;
                   format_value: a value short, for display

This instrument:
diffractometer.py  SingleCrystalDiffractometer(sample, params), the single-crystal
                   diffractometer: makes its own components, each knowing where it sits; params,
                   update_params (Params: its control parameters), instr_params, positions
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
from .diffractometer import DEFAULT_PARAMS, Params, SingleCrystalDiffractometer
from .params import InstrParam
from .samples import aluminum, la2ni7

__all__ = [
    "DEFAULT_PARAMS",
    "Arm",
    "Component",
    "InstrParam",
    "Monitor",
    "Monitor_nD",
    "Params",
    "Progress_bar",
    "SingleCrystalDiffractometer",
    "Single_crystal",
    "Slit",
    "Source_simple",
    "aluminum",
    "la2ni7",
]
