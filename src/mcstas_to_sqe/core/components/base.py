"""Base class of every component."""

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any

from mcstas_to_sqe.core.utils import format_value

if TYPE_CHECKING:
    from mcstasscript.interface.instr import McStas_instr

    from mcstas_to_sqe.core.base import Instrument


@dataclass(kw_only=True, repr=False)  # repr: its own, below; each subclass keeps it
class Component:
    """Base class of a McStas component.

    A subclass is named after the McStas component it stands for (``Slit``,
    ``Single_crystal``, ...). Its fields are its McStas parameters, plus the placement below.

    Parameters
    ----------
    at:
        Position (x, y, z) in m, relative to ``relative``, as McStas AT.
    rotated:
        Rotation (about x, y, z) in deg, relative to ``relative``, as McStas ROTATED.
    relative:
        Name of the component that ``at`` and ``rotated`` are relative to.
        If ``None``, they are absolute (lab frame).

    Attributes
    ----------
    name:
        Name of the attribute the component is set on in its instrument; also its McStas
        instance name and the name a ``relative`` refers to. ``None`` until the instrument sets
        it.
    component_name:
        McStas component, the class name.

    Notes
    -----
    Neither ``name`` nor ``component_name`` is a field, so neither is saved nor compared.

    Any value an instrument parameter provides is given as the parameter's name, or an
    expression of them, instead of a number, as in McStas. A component does not know which of
    its values a run sets: the instrument declares its instrument parameters.

    A component does not know the file it came from. A value that follows from its own values is
    computed when used; one that depends on other components is left to the instrument.

    A subclass that computes McStas parameters overrides :meth:`mcstas_parameters` and adds them
    to ``super()``'s. It computes them from its own values or its references to other
    components, never from numbers of its own. The fields it computes from stay in the result;
    the builder leaves out those McStas does not know.
    """

    at: list[float | str]
    rotated: list[float | str] = field(default_factory=lambda: [0, 0, 0])
    relative: str | None = None

    name = None  # its name in the instrument: the instrument sets it (no field)

    def __post_init__(self) -> None:
        self.component_name = type(self).__name__  # the McStas component (no field)

    def mcstas_parameters(self, inst: "Instrument") -> dict[str, Any]:
        """Return the McStas parameters of the component.

        Parameters
        ----------
        inst:
            The instrument the component belongs to.

        Returns
        -------
        :
            Values by McStas parameter name: every field except the placement (``at``,
            ``rotated``, ``relative``), which McStas takes as AT, ROTATED and RELATIVE instead.
        """
        skip = {"at", "rotated", "relative"}
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}

    def add_to(self, instr: "McStas_instr") -> Any:
        """Add the component to a McStasScript instrument.

        It is added as McStas component :attr:`component_name`, named :attr:`name`, and placed
        at ``at``/``rotated``/``relative``. Its McStas parameters are not set.

        Parameters
        ----------
        instr:
            The McStasScript instrument.

        Returns
        -------
        :
            The new McStasScript component.

        Raises
        ------
        ValueError
            If the component has no :attr:`name` yet, i.e. is not set on an instrument.
        """
        if self.name is None:
            raise ValueError(f"a {self.component_name} with no name: set it on an instrument first")
        return instr.add_component(
            self.name,
            self.component_name,
            AT=list(self.at),
            ROTATED=list(self.rotated),
            RELATIVE=self.relative or "ABSOLUTE",  # of both AT and ROTATED
        )

    def __repr__(self) -> str:
        """Show the McStas component and its values as a table, one row per field."""
        from tabulate import tabulate  # only when printed: importing does not need it

        rows = [(f.name, format_value(getattr(self, f.name))) for f in fields(self)]
        return f"{self.component_name}:\n{tabulate(rows, ('parameter', 'value'))}"
