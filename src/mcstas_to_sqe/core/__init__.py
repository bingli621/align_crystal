"""Entities shared by all instruments.

An instrument is a set of components. This package holds no files and no McStas code, although
each component provides its McStas parameters. It imports nothing else from mcstas_to_sqe:
instruments/ and samples/ build on it, and io/ and mcstas/ are adapters around them.

Modules
-------
base
    :class:`Instrument`, the base class of every instrument, and ``INSTRUMENTS``, every
    instrument class by name. io/ and mcstas/ work with any of them.
components
    The components, one dataclass each, derived from :class:`Component`.
params
    ``param``, a control parameter with unit and comment, and :class:`InstrParam`, one McStas
    instrument parameter.
geometry
    ``rotation`` and ``place_absolute``: where the components are in the lab frame, as McStas
    places them.
utils
    ``evaluate``, the value of a McStas expression of instrument parameters, and
    ``format_value``, a short form of a value for display.
"""

from .base import INSTRUMENTS, Instrument
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
from .params import InstrParam

__all__ = [
    "INSTRUMENTS",
    "Arm",
    "Component",
    "InstrParam",
    "Instrument",
    "Monitor",
    "Monitor_nD",
    "Progress_bar",
    "Single_crystal",
    "Slit",
    "Source_simple",
]
