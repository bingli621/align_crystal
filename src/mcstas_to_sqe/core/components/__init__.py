"""Building blocks of an instrument: one dataclass per McStas component.

Components carry almost no defaults of their own (see instruments/diffractometer/;
``Single_crystal`` has a few) and know nothing about files. Each provides its McStas parameters
through ``mcstas_parameters`` (its fields plus anything it computes), but imports no McStas code.

A value that follows from a component's own values is a property computed when used, such as the
crystal's reciprocal vectors. A value that depends on other components, such as the positions, is
left to the instrument.
"""

from .base import Component
from .crystal import Single_crystal
from .detector import Monitor, Monitor_nD
from .misc import Arm, Progress_bar, Slit
from .source import Source_simple

# every component class by its McStas component name: what a section's `component:` in a
# parameters file refers to
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
