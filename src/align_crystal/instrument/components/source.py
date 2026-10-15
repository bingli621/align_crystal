"""The neutron source."""

from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True)
class Source_simple(Component):
    """A monochromatic source."""

    radius: float  # m
    focus_on: str  # name of the component the source focuses on
    dist: float | None  # source -> focus plane, m; None = z of `focus_on` in the source frame
    flux: float
    E0: float  # meV, or the name of the control parameter that gives it
