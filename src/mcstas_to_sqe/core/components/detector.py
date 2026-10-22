"""Monitors and detectors."""

from dataclasses import dataclass

from .base import Component


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Monitor(Component):
    xwidth: float  # m
    yheight: float  # m
    restore_neutron: int  # 1: the neutrons carry on


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Monitor_nD(Component):
    radius: float  # m
    theta_limits: list  # deg, signed: negative = right of the beam
    theta_bins: int
    ymin: float  # m: its height, from ymin to ymax
    ymax: float  # m
    y_bins: int  # over ymin to ymax
    options: str  # the other McStas options (shape, list), after theta and y
    filename: str  # the output file's name
    nexus_bins: int  # 1: the event list in the NeXus file
    restore_neutron: int  # 1: the neutrons carry on

    def mcstas_parameters(self, inst):
        """Its fields, with theta and y (over ymin to ymax, McStas's default) put into its
        options, before its other options."""
        lo, hi = self.theta_limits
        theta = f"theta limits=[{lo} {hi}] bins={self.theta_bins}"
        options = f"{theta}, y bins={self.y_bins}, {self.options}"
        return super().mcstas_parameters(inst) | {"options": options}
