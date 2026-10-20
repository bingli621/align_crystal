"""The components that fit no other file: Progress_bar, Slit, Arm."""

from dataclasses import dataclass

from .base import Component


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Progress_bar(Component):
    pass


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Slit(Component):
    xwidth: float  # opening, m
    yheight: float  # opening, m


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Arm(Component):
    """A reference frame (a goniometer axis, when its `rotated` uses an instrument parameter)."""
