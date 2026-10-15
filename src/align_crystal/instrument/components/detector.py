"""Monitors and detectors."""

from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True)
class Monitor(Component):
    pass


@dataclass(kw_only=True)
class Monitor_nD(Component):
    radius: float  # m
    yheight: float  # m
    two_theta_range: list  # deg, signed: negative = right of the beam
    n_theta: int
    n_y: int
