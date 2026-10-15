"""The neutron source."""

from dataclasses import dataclass
from typing import ClassVar

from .misc import Component


@dataclass(kw_only=True)
class Source_simple(Component):
    """A monochromatic source."""

    OPTIONAL: ClassVar[tuple] = (*Component.OPTIONAL, "dist")  # None: computed when used

    radius: float  # m
    focus_on: str  # name of the component the source focuses on
    flux: float
    E0: float  # meV, or the name of the control parameter that gives it
    dist: float | None = (
        None  # source -> focus plane, m; None = z of `focus_on` (see SingleCrystalDiffractometer.source_dist)
    )
