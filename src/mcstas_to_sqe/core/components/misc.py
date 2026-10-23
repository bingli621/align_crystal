"""Components that fit no other module: Progress_bar, Slit, Arm."""

from dataclasses import dataclass

from .base import Component


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Progress_bar(Component):
    """McStas ``Progress_bar``, which reports simulation progress.

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.
    """


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Slit(Component):
    """A rectangular slit, as McStas ``Slit``.

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.

    Parameters
    ----------
    xwidth, yheight:
        Opening in m.
    """

    xwidth: float
    yheight: float


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Arm(Component):
    """A reference frame, as McStas ``Arm``.

    An arm whose ``rotated`` uses an instrument parameter acts as a goniometer axis.
    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.
    """
