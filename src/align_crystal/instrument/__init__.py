"""The entities: an instrument is a set of components (no files, no McStas code, though each
component gives its McStas parameters; io/ and mcstas/ are adapters around them and the only ones
importing from here).

Generic, for any instrument:
base.py            Instrument, the base of any instrument (components, params, instr_params,
                   positions); INSTRUMENTS, every one by class name. io/ and mcstas/ work with any
components/        the components, one dataclass each (base.py: Component;
                   misc.py, source.py, detector.py, crystal.py)
samples/           the ready-made samples (aluminum, la2ni7), with their CIF files
params.py          param: a control parameter with its unit and comment; InstrParam: one McStas
                   instrument parameter
geometry.py        rotation, place_absolute: where the components are in the lab frame, as McStas
                   places them
utils.py           evaluate: the number a McStas expression of instrument parameters stands for;
                   format_value: a value short, for display

This instrument:
diffractometer.py  SingleCrystalDiffractometer(sample, params), an Instrument: makes its own
                   components around the sample; its control parameters Params, DEFAULT_PARAMS;
                   instr_params: the wavelength of ei, and the goniometer angles
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
from .diffractometer import DEFAULT_PARAMS, Params, SingleCrystalDiffractometer
from .params import InstrParam
from .samples import aluminum, la2ni7

__all__ = [
    "DEFAULT_PARAMS",
    "INSTRUMENTS",
    "Arm",
    "Component",
    "InstrParam",
    "Instrument",
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
