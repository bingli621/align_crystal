"""The building blocks of an instrument: one dataclass per McStas component.

They carry almost no defaults of their own (see instrument/model/diffractometer.py; Single_crystal has a
few) and know nothing about files or McStas. A value that follows from a component's own values is a
property computed when used (the crystal's reciprocal vectors); one that depends on other components
is left to the diffractometer (the source's focus distance, `source_dist`).

misc.py     the base `Component`, and the simple ones: Progress_bar, Slit, Arm
source.py    Source_simple
detector.py  Monitor, Monitor_nD
sample.py    Single_crystal
"""

from .detector import Monitor, Monitor_nD
from .misc import Arm, Component, Progress_bar, Slit
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
