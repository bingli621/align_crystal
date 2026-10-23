"""Monitors and detectors."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import Component

if TYPE_CHECKING:
    from mcstas_to_sqe.core.base import Instrument


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Monitor(Component):
    """A flat counting monitor, as McStas ``Monitor``.

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.

    Parameters
    ----------
    xwidth, yheight:
        Size in m.
    restore_neutron:
        1 lets the neutrons carry on past the monitor.
    """

    xwidth: float
    yheight: float
    restore_neutron: int


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Monitor_nD(Component):
    """A detector binned in scattering angle and height, as McStas ``Monitor_nD``.

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.

    Parameters
    ----------
    radius:
        Radius in m.
    theta_limits:
        Angular range ``[min, max]`` in deg, signed: negative is right of the beam.
    theta_bins:
        Number of angular bins.
    ymin, ymax:
        Vertical extent in m.
    y_bins:
        Number of bins from ``ymin`` to ``ymax``.
    options:
        Further McStas options (shape, list), appended after theta and y.
    filename:
        Name of the output file.
    nexus_bins:
        1 writes the event list to the NeXus file.
    restore_neutron:
        1 lets the neutrons carry on past the detector.
    """

    radius: float
    theta_limits: list[float]
    theta_bins: int
    ymin: float
    ymax: float
    y_bins: int
    options: str
    filename: str
    nexus_bins: int
    restore_neutron: int

    def mcstas_parameters(self, inst: "Instrument") -> dict[str, Any]:
        """Return the McStas parameters, with theta and y binning put into ``options``.

        Parameters
        ----------
        inst:
            The instrument the detector belongs to.

        Returns
        -------
        :
            The fields, with ``options`` replaced by the theta and y binning followed by the
            given options. y spans ``ymin`` to ``ymax``, McStas's default.
        """
        lo, hi = self.theta_limits
        theta = f"theta limits=[{lo} {hi}] bins={self.theta_bins}"
        options = f"{theta}, y bins={self.y_bins}, {self.options}"
        return super().mcstas_parameters(inst) | {"options": options}
