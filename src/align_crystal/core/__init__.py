"""The entities: the diffractometer is a set of components (no McStas knowledge).

components/        the components, one dataclass each (misc.py, source.py, detector.py, sample.py)
diffractometer.py  SingleCrystalDiffractometer: its components, each knowing where it sits
params.py          DesignParam: the design parameters, as one nested dict;
                   ControlParam: the control parameters (McStas instrument parameters) it declares
cif/               a plain folder: the CIF files of the ready-made crystals (aluminium, la2ni7)
params.yaml        the default parameters, in beam order
builder.py         build_diffractometer(): the same defaults, made in code
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
from .builder import build_diffractometer
from .params import Control, ControlParam, DesignParam
from .components.sample import aluminium, la2ni7

__all__ = [
    "Arm",
    "aluminium",
    "Component",
    "Control",
    "ControlParam",
    "DesignParam",
    "build_diffractometer",
    "la2ni7",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "SingleCrystalDiffractometer",
    "Slit",
    "Source_simple",
]
