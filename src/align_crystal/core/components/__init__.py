"""The building blocks of an instrument: one dataclass per McStas component.

They carry almost no defaults of their own (see core/params.yaml; Single_crystal has a few) and know nothing about files or
McStas. A value a component can calculate from its own other values is derived in `__post_init__`
when it is null; what depends on other components is left to the diffractometer's own
`__post_init__` (see core/diffractometer.py).

misc.py     the base `Component`, and the simple ones: Progress_bar, Slit, Arm
source.py    Source_simple
detector.py  Monitor, Monitor_nD
sample.py    Single_crystal
"""

from .misc import Arm, Component, Progress_bar, Slit
from .detector import Monitor, Monitor_nD
from .sample import Single_crystal
from .source import Source_simple

# every component class by its McStas component name: what a section's `component:` in a parameters file refers to
COMPONENTS = {
    c.__name__: c
    for c in (
        Arm,
        Monitor,
        Monitor_nD,
        Progress_bar,
        Single_crystal,
        Slit,
        Source_simple,
    )
}

__all__ = [
    "COMPONENTS",
    "Arm",
    "Component",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
