"""The neutron source."""

from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True)
class Source_simple(Component):
    """A monochromatic source."""

    radius: float  # m
    focus_on: str  # name of the component the source focuses on
    flux: float
    lambda0: float | str = (
        "wavelength"  # angstrom, or the name of the instrument parameter that gives it
    )
    dist: float | None = (
        None  # source -> focus plane, m; None = z of `focus_on` (see SingleCrystalDiffractometer.source_dist)
    )
