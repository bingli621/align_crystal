"""The entities: the diffractometer is a set of components (no McStas knowledge).

components/        the components, one dataclass each (misc.py, source.py, detector.py, sample.py)
model/             the diffractometer and its parameters:
                   diffractometer.py  SingleCrystalDiffractometer: its components, each knowing where it sits
                   params.py          DesignParam: the design parameters, as one nested dict;
                                      ControlParam: the control parameters (McStas instrument parameters)
                   params.yaml        the default parameters, in beam order
cif/               a plain folder: the CIF files of the ready-made crystals (aluminum, la2ni7)
builder.py         build_diffractometer(): the same defaults, made in code
"""

from .builder import build_diffractometer
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
from .model.params import Control, ControlParam, DesignParam

__all__ = [
    "Arm",
    "Component",
    "Control",
    "ControlParam",
    "DesignParam",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "SingleCrystalDiffractometer",
    "Single_crystal",
    "Slit",
    "Source_simple",
    "aluminum",
    "build_diffractometer",
    "la2ni7",
]
