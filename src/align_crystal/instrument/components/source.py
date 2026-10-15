"""The neutron source."""

import math
from dataclasses import dataclass
from typing import ClassVar

from .misc import Component


@dataclass(kw_only=True)
class Source_simple(Component):
    """A monochromatic source."""

    OPTIONAL: ClassVar[tuple] = (*Component.OPTIONAL, "dist", "ei")  # None: computed / not set

    radius: float  # m
    focus_on: str  # name of the component the source focuses on
    flux: float
    ei: float | None = None  # incident energy, meV: given when the instrument is made
    lambda0: float | str = (
        "wavelength"  # angstrom, or the name of the instrument parameter that gives it
    )
    dist: float | None = (
        None  # source -> focus plane, m; None = z of `focus_on` (see SingleCrystalDiffractometer.source_dist)
    )

    @property
    def wavelength(self) -> float:
        """The wavelength of `ei`, angstrom: sqrt(81.80421 / ei[meV]), the value of the instrument parameter `lambda0` names."""
        if self.ei is None:
            raise ValueError("The incident energy `ei` is not set")
        return math.sqrt(81.80421 / self.ei)
