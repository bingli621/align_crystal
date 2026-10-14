"""The entities: the diffractometer is a set of components (no McStas knowledge).

components/        the kinds of component, one dataclass each (misc.py, source.py, detector.py, sample.py)
diffractometer.py  SingleCrystalDiffractometer: its components, each knowing where it sits
params.py          DesignParam: the design parameters, as one nested dict;
                   ControlParam: the control parameters (McStas instrument parameters) it declares
params.yaml        the default parameters, in beam order
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
from .params import ControlParam, DesignParam

__all__ = [
    "Arm",
    "Component",
    "ControlParam",
    "DesignParam",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "SingleCrystalDiffractometer",
    "Slit",
    "Source_simple",
]
