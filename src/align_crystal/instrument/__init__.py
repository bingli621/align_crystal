"""Instruments as configurations (no McStas knowledge, see mcstas/ for that).

components/     the kinds of component, one dataclass each (misc.py, source.py, detector.py, sample.py)
instrument.py   Instrument: the components of an instrument, each with its placement
diffractometer/   Diffractometer(Instrument): its components (diffractometer.py) and defaults (params.yaml)
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
from .diffractometer import Diffractometer
from .instrument import Instrument

__all__ = [
    "Arm",
    "Component",
    "Diffractometer",
    "Instrument",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
