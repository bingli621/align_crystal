"""The entities: the diffractometer is a set of components (no McStas knowledge).

Generic, for any instrument:
components/        the components, one dataclass each (misc.py, source.py, detector.py, sample.py)
params.py          DesignParam: the design parameters, as one nested dict;
                   InstrumentParam: the instrument parameters (McStas instrument parameters);
                   ControlParam: what is given when the instrument is made (the energy)
cif/               a plain folder: the CIF files of the ready-made crystals (aluminum, la2ni7)

model/             this instrument, the single-crystal diffractometer:
  diffractometer.py  SingleCrystalDiffractometer: its components, each knowing where it sits
  builder.py         build_diffractometer(): the default made in code, with a file laid over it
  params.yaml        build_diffractometer() saved: a reference of how a parameters file looks
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
from .model.builder import PARAMS_FILE, build_diffractometer
from .model.diffractometer import SingleCrystalDiffractometer
from .params import ControlParam, DesignParam, InstrumentParam, InstrumentParameter, merge

__all__ = [
    "PARAMS_FILE",
    "Arm",
    "Component",
    "ControlParam",
    "DesignParam",
    "InstrumentParam",
    "InstrumentParameter",
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
    "merge",
]
