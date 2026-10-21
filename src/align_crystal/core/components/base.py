"""The base of every component: Component."""

from dataclasses import dataclass, field, fields

from ..utils import format_value


@dataclass(kw_only=True, repr=False)  # repr: its own, below; each subclass keeps it
class Component:
    """One piece of the instrument. A subclass is named after the McStas component it stands for
    (Slit, Single_crystal, ...); a component saves it as its `component_name` when created.
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

    Its McStas parameters (`mcstas_parameters`) are its fields, as they are. A subclass that
    computes some (from its values or its references to other components, never a number of its
    own) overrides it: it adds what it computes to `super()`'s. The fields it computes from stay;
    the builder leaves out the ones McStas does not know.
    """

    at: list
    rotated: list = field(default_factory=lambda: [0, 0, 0])
    relative: str | None = None

    name = None  # its name in the instrument: the instrument sets it (no field)

    def __post_init__(self):
        self.component_name = type(self).__name__  # the McStas component (no field)

    def mcstas_parameters(self, inst) -> dict:
        """Its McStas parameters, in the instrument `inst`: its fields, but where it sits (McStas
        AT, ROTATED, RELATIVE: no parameters)."""
        skip = {"at", "rotated", "relative"}
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}

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
