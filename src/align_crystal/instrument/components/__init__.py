"""The building blocks of an instrument: one dataclass per kind of component.

They carry no defaults of their own (see diffractometer/params.yaml) and know nothing about files
or McStas. A value a component can calculate from its own other values is derived in
`__post_init__` when it is null; what depends on other components is derived by the instrument in
its own `__post_init__` (see diffractometer/diffractometer.py).

misc.py     the base `Component`, and the simple ones: Progress_bar, Slit, Arm
source.py    Source_simple
detector.py  Monitor, Monitor_nD
sample.py    Single_crystal
"""

from .misc import Arm, Component, Progress_bar, Slit
from .detector import Monitor, Monitor_nD
from .sample import Single_crystal
from .source import Source_simple

__all__ = [
    "Arm",
    "Component",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
