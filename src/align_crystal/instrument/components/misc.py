"""The base `Component` and the components that fit no other file: Progress_bar, Slit, Arm."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(kw_only=True)
class Component:
    """One piece of the instrument. A subclass is named after the McStas component it stands for
    (Slit, Single_crystal, ...), so `type(component).__name__` is the McStas component.
    Its role is its key in the config; `name` optionally gives it a different McStas instance
    name (default: the role).

    It also records where it sits, as McStas AT and ROTATED: `at` (m) and `rotated` (deg, numbers
    or parameter names), both relative to the component with role `relative` (None = absolute).
    """

    at: list
    rotated: list | None
    relative: str | None
    name: str | None = None
    OPTIONAL: ClassVar[tuple] = ("name", "rotated", "relative")  # fields that may stay None


@dataclass(kw_only=True)
class Progress_bar(Component):
    pass


@dataclass(kw_only=True)
class Slit(Component):
    size: float  # opening and source focus (x and y), m


@dataclass(kw_only=True)
class Arm(Component):
    """A reference frame. A goniometer arm has an `angle` (deg): the initial value of the
    instrument parameter that rotates it (see `rotated`)."""

    angle: float | None = None
    OPTIONAL: ClassVar[tuple] = (*Component.OPTIONAL, "angle")
