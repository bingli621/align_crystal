"""The neutron source."""

import math
from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Source_simple(Component):
    """A monochromatic source."""

    radius: float  # m
    focus_on: str  # name of the component the source focuses on (at its distance, in McStas)
    focus_xw: float  # m
    focus_yh: float  # m
    flux: float
    lambda0: float | str = (
        "wavelength"  # angstrom, or the name of the instrument parameter that gives it
    )
    dlambda: float  # wavelength spread, angstrom: 0 = monochromatic

    @staticmethod
    def wavelength_from_ei(ei: float) -> float:
        """The neutron wavelength of the energy `ei` (meV), angstrom: sqrt(81.80421 / ei)."""
        return math.sqrt(81.80421 / ei)
