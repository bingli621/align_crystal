"""Entities shared by all instruments.

An instrument is a set of components. This package holds no files and no McStas code, although
each component provides its McStas parameters, and it imports nothing else from mcstas_to_sqe.
The package layout is described in README.md.
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
