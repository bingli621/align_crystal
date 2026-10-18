"""The base `Component` and the components that fit no other file: Progress_bar, Slit, Arm."""

from dataclasses import dataclass, field, fields

from align_crystal.instrument.utils import format_value


@dataclass(kw_only=True, repr=False)  # repr: its own, below; each subclass keeps it
class Component:
    """One piece of the instrument. A subclass is named after the McStas component it stands for
    (Slit, Single_crystal, ...), so `type(component).__name__` is the McStas component.
    Its name (the one that `relative` refers to, and its McStas instance name) is the name of its
    field in the diffractometer; the component does not hold it. What follows from its own values
    is computed when used; the rest is left to the diffractometer. It knows nothing of the file it
    came from.

    It also records where it sits, as McStas AT and ROTATED: `at` (m) and `rotated` (deg, numbers
    or instrument parameter names; default [0, 0, 0]), both relative to the component named
    `relative` (None = absolute).

    A component does not know which of its values a run sets: the instrument declares its
    instrument parameters, and, as in McStas, a value an instrument parameter gives is the
    parameter's name (or an expression of them) instead of a number.
    """

    at: list
    rotated: list = field(default_factory=lambda: [0, 0, 0])
    relative: str | None = None

    def __repr__(self):
        """Its McStas component and its values, as a table: one row per value."""
        from tabulate import tabulate  # only when printed: importing does not need it

        rows = [(f.name, format_value(getattr(self, f.name))) for f in fields(self)]
        return f"{type(self).__name__}:\n{tabulate(rows, ('parameter', 'value'))}"


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Progress_bar(Component):
    pass


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Slit(Component):
    xwidth: float  # opening (and source focus), m
    yheight: float  # opening (and source focus), m


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Arm(Component):
    """A reference frame (a goniometer axis, when its `rotated` uses an instrument parameter)."""
