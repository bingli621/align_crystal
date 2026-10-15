"""The entities: the diffractometer is a set of components (no McStas knowledge).

Generic, for any instrument:
components/        the components, one dataclass each (misc.py, source.py, detector.py, sample.py)
params.py          DesignParam: the design parameters, as one nested dict;
                   ControlParam: the control parameters (McStas instrument parameters)
cif/               a plain folder: the CIF files of the ready-made crystals (aluminum, la2ni7)

model/             this instrument, the single-crystal diffractometer:
  diffractometer.py  SingleCrystalDiffractometer: its components, each knowing where it sits
  builder.py         build_diffractometer(): the same defaults, made in code
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
from .components.sample import aluminum, la2ni7
from .model.builder import build_diffractometer
from .model.diffractometer import SingleCrystalDiffractometer
from .params import Control, ControlParam, DesignParam

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
