"""The neutron source."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import Component

if TYPE_CHECKING:
    from mcstas_to_sqe.core.base import Instrument


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Source_simple(Component):
    """A circular source of a wavelength band, as McStas ``Source_simple``.

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.

    Parameters
    ----------
    radius:
        Radius in m.
    focus_on:
        Name of the component the source focuses on, at that component's distance.
    focus_xw, focus_yh:
        Width and height of the focusing target in m.
    flux:
        Source flux.
    lambda0:
        Mean wavelength in Å, or the name of the instrument parameter that provides it.
    dlambda:
        Wavelength spread in Å. 0 is monochromatic.
    """

    radius: float
    focus_on: str
    focus_xw: float
    focus_yh: float
    flux: float
    lambda0: float | str = "wavelength"
    dlambda: float

    def mcstas_parameters(self, inst: "Instrument") -> dict[str, Any]:
        """Return the McStas parameters, with the distance to ``focus_on``.

        Parameters
        ----------
        inst:
            The instrument the source belongs to, which gives the positions.

        Returns
        -------
        :
            The fields, plus ``dist``: the distance in m to the component ``focus_on``.

        Raises
        ------
        ValueError
            If ``focus_on`` is not a component of ``inst``.
        """
        positions = inst.positions()
        if self.focus_on not in positions:
            raise ValueError(f"{self.name}: focus_on {self.focus_on!r} is no component")
        dist = math.dist(positions[self.name], positions[self.focus_on])
        return super().mcstas_parameters(inst) | {"dist": dist}

    @staticmethod
    def wavelength_from_ei(ei: float) -> float:
        """Convert a neutron energy to its wavelength.

        Parameters
        ----------
        ei:
            Energy in meV.

        Returns
        -------
        :
            Wavelength in Å, ``sqrt(81.80421 / ei)``.
        """
        return math.sqrt(81.80421 / ei)
