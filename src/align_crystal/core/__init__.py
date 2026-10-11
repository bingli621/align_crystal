"""The entities: an instrument is a set of components (no file or McStas knowledge).

components/     the kinds of component, one dataclass each (misc.py, source.py, detector.py, sample.py)
instrument.py   Instrument: the components of an instrument, each with its placement
params.py       Param: all the parameters of an instrument, as one nested dict
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
from .instrument import Instrument
from .params import Param

__all__ = [
    "Arm",
    "Component",
    "Instrument",
    "Param",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
