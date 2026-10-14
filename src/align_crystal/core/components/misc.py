"""The base `Component` and the components that fit no other file: Progress_bar, Slit, Arm."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(kw_only=True)
class Component:
    """One piece of the instrument. A subclass is named after the McStas component it stands for
    (Slit, Single_crystal, ...), so `type(component).__name__` is the McStas component.
    Its `name` is its McStas instance name; its key in the instrument is its role, the one that
    `relative` refers to. If the name is not given it is the role (the diffractometer does that). A
    component fills in, in its `__post_init__`, the values that follow from its own; the rest is
    left to the diffractometer. It knows nothing of the file it came from.

    It also records where it sits, as McStas AT and ROTATED: `at` (m) and `rotated` (deg, numbers
    or control parameter names), both relative to the component with role `relative` (None =
    absolute).

    A component does not know which of its values a run controls: the instrument declares its
    control parameters, and, as in McStas, a value a control gives is the control's name (or an
    expression of them) instead of a number.
    """

    at: list
    rotated: list | None = None
    relative: str | None = None
    name: str | None = None
    OPTIONAL: ClassVar[tuple] = (
        "name",
        "rotated",
        "relative",
    )  # fields that may stay None


@dataclass(kw_only=True)
class Progress_bar(Component):
    pass


@dataclass(kw_only=True)
class Slit(Component):
    size: float  # opening and source focus (x and y), m


@dataclass(kw_only=True)
class Arm(Component):
    """A reference frame (a goniometer axis, when its `rotated` uses a control parameter)."""
