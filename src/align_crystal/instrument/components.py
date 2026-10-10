"""The building blocks of an instrument: one dataclass per kind of component.

They carry no defaults of their own (see params.yaml) and know nothing about files or McStas.
A value a component can calculate from its own other values is derived in `__post_init__` when
it is null; what depends on other components is derived by the instrument in its own
`__post_init__` (see diffractometer.py).
"""

import math
from dataclasses import dataclass
from typing import ClassVar


@dataclass(kw_only=True)
class Component:
    """One piece of the instrument. A subclass is named after the McStas component it stands for
    (Slit, Single_crystal, ...), so `type(component).__name__` is the McStas component.
    Its role is its key in the config; `name` optionally gives it a different McStas instance
    name (default: the role).

    It also records where it sits, as McStas AT and ROTATED: `at` (m) and `rotated` (deg, numbers
    or parameter names), both relative to the component with role `relative` (None = absolute).
    """

    at: list
    rotated: list | None
    relative: str | None
    name: str | None = None
    OPTIONAL: ClassVar[tuple] = ("name", "rotated", "relative")  # fields that may stay None


@dataclass(kw_only=True)
class Progress_bar(Component):
    pass


@dataclass(kw_only=True)
class Source_simple(Component):
    energy_meV: float
    wavelength: float | None  # angstrom, monochromatic; None = derive from energy_meV
    radius: float  # m
    dist: float | None  # source -> focus plane, m; None = derived by the instrument
    flux: float

    def __post_init__(self):
        if self.wavelength is None:
            self.wavelength = math.sqrt(81.80421 / self.energy_meV)  # lambda[A]=sqrt(81.804/E[meV])


@dataclass(kw_only=True)
class Slit(Component):
    size: float  # opening and source focus (x and y), m


@dataclass(kw_only=True)
class Monitor(Component):
    pass


@dataclass(kw_only=True)
class Arm(Component):
    """A reference frame. A goniometer arm has an `angle` (deg): the initial value of the
    instrument parameter that rotates it (see `rotated`)."""

    angle: float | None = None
    OPTIONAL: ClassVar[tuple] = (*Component.OPTIONAL, "angle")


@dataclass(kw_only=True)
class Single_crystal(Component):
    size: float  # cube edge, m
    order: int  # 1 = single scattering only


@dataclass(kw_only=True)
class Monitor_nD(Component):
    radius: float  # m
    height: float  # m
    two_theta_range: list  # deg, signed: negative = right of the beam
    n_theta: int
    n_y: int
