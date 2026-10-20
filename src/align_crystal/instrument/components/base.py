"""The base of every component: Component."""

from dataclasses import dataclass, field, fields
from typing import ClassVar

from align_crystal.instrument.utils import format_value


@dataclass(kw_only=True, repr=False)  # repr: its own, below; each subclass keeps it
class Component:
    """One piece of the instrument. A subclass says the McStas component it stands for in
    `component_name` (Slit, Single_crystal, ...), and is named after it; a subclass of it keeps it.
    Its `name` (the one that `relative` refers to, and its McStas instance name) is the name of
    its attribute in the instrument, which sets it when the component is set on it (None until
    then). Neither is a field, so neither is saved nor compared.
    What follows from its own values is computed when used; the rest is left to the instrument.
    It knows nothing of the file it came from.

    It also records where it sits, as McStas AT and ROTATED: `at` (m) and `rotated` (deg, numbers
    or instrument parameter names; default [0, 0, 0]), both relative to the component named
    `relative` (None = absolute).

    A component does not know which of its values a run sets: the instrument declares its
    instrument parameters, and, as in McStas, a value an instrument parameter gives is the
    parameter's name (or an expression of them) instead of a number.

    Its McStas parameters (`mcstas_values`) are its fields, as they are, and what it computes
    (`mcstas_computed`): from its values or its references to other components, never a number of
    its own. A subclass names the fields it computes from in `mcstas_uses`, so they are not passed
    through.
    """

    at: list
    rotated: list = field(default_factory=lambda: [0, 0, 0])
    relative: str | None = None

    name = None  # its name in the instrument: the instrument sets it (no field)
    component_name: ClassVar[str]  # the McStas component: a subclass sets it
    mcstas_uses: ClassVar[tuple] = ()  # the fields `mcstas_computed` takes, not passed through

    def mcstas_computed(self, inst) -> dict:
        """The McStas parameters that follow from its values (in the instrument `inst`): none
        here."""
        return {}

    def mcstas_values(self, inst) -> dict:
        """Its McStas parameters, in the instrument `inst`: its fields (but where it sits,
        and `mcstas_uses`), and what it computes. Raises if it computes one of those fields."""
        skip = {"at", "rotated", "relative", *self.mcstas_uses}
        own = {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}
        computed = self.mcstas_computed(inst)
        if overwritten := sorted(own.keys() & computed.keys()):
            raise ValueError(
                f"{self.name} ({self.component_name}): it computes its fields {overwritten}"
            )
        return own | computed

    def add_to(self, instr):
        """Add it to the McStasScript instrument `instr` as its `name`, and return the McStasScript
        component: the McStas component is its `component_name`, the position its
        at/rotated/relative."""
        if self.name is None:
            raise ValueError(f"a {self.component_name} with no name: set it on an instrument first")
        return instr.add_component(
            self.name,
            self.component_name,
            AT=list(self.at),
            ROTATED=list(self.rotated),
            RELATIVE=self.relative or "ABSOLUTE",  # of both AT and ROTATED
        )

    def __repr__(self):
        """Its McStas component and its values, as a table: one row per value."""
        from tabulate import tabulate  # only when printed: importing does not need it

        rows = [(f.name, format_value(getattr(self, f.name))) for f in fields(self)]
        return f"{self.component_name}:\n{tabulate(rows, ('parameter', 'value'))}"
