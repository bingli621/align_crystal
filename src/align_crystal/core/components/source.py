"""The neutron source."""

import math
from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True)
class Source_simple(Component):
    energy_meV: float
    wavelength: float | None  # angstrom, monochromatic; None = derive from energy_meV
    radius: float  # m
    focus_on: str  # role of the component the source focuses on
    dist: float | None  # source -> focus plane, m; None = z of `focus_on` in the source frame
    flux: float

    def __post_init__(self):
        if self.wavelength is None:
            self.wavelength = math.sqrt(81.80421 / self.energy_meV)  # lambda[A]=sqrt(81.804/E[meV])
