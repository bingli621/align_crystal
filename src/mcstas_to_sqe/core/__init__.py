"""The entities any instrument shares: an instrument is a set of components (no files, no McStas
code, though each component gives its McStas parameters). It imports nothing else of the package:
instruments/ (the instruments themselves) and samples/ (the ready-made samples) build on it, and
io/ and mcstas/ are adapters around them.

base.py            Instrument, the base of any instrument (components, params, instr_params,
                   positions); INSTRUMENTS, every one by class name. io/ and mcstas/ work with any
components/        the components, one dataclass each (base.py: Component;
                   misc.py, source.py, detector.py, crystal.py)
params.py          param: a control parameter with its unit and comment; InstrParam: one McStas
                   instrument parameter
geometry.py        rotation, place_absolute: where the components are in the lab frame, as McStas
                   places them
utils.py           evaluate: the number a McStas expression of instrument parameters stands for;
                   format_value: a value short, for display
"""

from .base import INSTRUMENTS, Instrument
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
from .params import InstrParam

__all__ = [
    "INSTRUMENTS",
    "Arm",
    "Component",
    "InstrParam",
    "Instrument",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
