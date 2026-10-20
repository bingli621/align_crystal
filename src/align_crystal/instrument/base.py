"""The base of any instrument: Instrument; and INSTRUMENTS, every instrument class by its name
(a subclass is added when it is defined: what a parameters file's `instrument:` names).

An instrument is its components, one attribute each, in the order of the beam (the attribute's
name is the one a `relative` refers to, and the McStas instance name), and its control parameters
(`params`: a frozen dataclass, the class's `params_class`, each field with its unit and comment in
its metadata; see `params.param`).

A subclass (e.g. `SingleCrystalDiffractometer`) sets, as class attributes, its `params_class` and
its McStas instrument `name`; makes its components in `__init__`, which must take `params` as a
keyword (io/ makes it with only that) and call `super().__init__(params)` first; and says which
McStas instrument parameters follow from its params (`instr_params`).

The rest is the same for every instrument, and io/ and mcstas/ rely only on it: `name`, `params`
and `update_params`, `components`, `instr_params`, `positions`, equality and the summary (repr).
"""

from dataclasses import asdict, fields, replace

from align_crystal.instrument.components import Component
from align_crystal.instrument.geometry import place_absolute
from align_crystal.instrument.params import InstrParam
from align_crystal.instrument.utils import format_value

INSTRUMENTS: dict[str, type] = {}  # every subclass of Instrument by its class name


class Instrument:
    """The components, one attribute each, in the order of the beam, and the control parameters
    (`params`). `components` gives the components as a dict by name, `instr_params` the McStas
    instrument parameters.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of an instrument parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    params_class: type  # the frozen dataclass of the control parameters: a subclass sets it
    name: str  # the McStas instrument name: a subclass sets it (an instance may change its own)

    def __init_subclass__(cls, **kwargs):
        """Add the subclass to INSTRUMENTS, by its class name."""
        super().__init_subclass__(**kwargs)
        INSTRUMENTS[cls.__name__] = cls

    def __setattr__(self, attr, value):
        """Set an attribute; a component set on it gets its name (the attribute's)."""
        if isinstance(value, Component):
            value.name = attr
        super().__setattr__(attr, value)

    def __init__(self, params=None):
        """Its control parameters `params` (a `params_class`; None: its defaults); a subclass then
        sets its components, in the order of the beam."""
        self._params = self.params_class() if params is None else params

    @property
    def params(self):
        """Its control parameters (frozen: `update_params` changes them)."""
        return self._params

    def update_params(self, **values):
        """Change control parameters, e.g. `update_params(ei=25)`; an unknown name raises."""
        self._params = replace(self._params, **values)

    @property
    def instr_params(self) -> list[InstrParam]:
        """The McStas instrument parameters, calculated from the params: a subclass says which."""
        raise NotImplementedError

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam (one set to None left out): its
        attributes that are components, in the order `__init__` first sets them."""
        return {n: v for n, v in vars(self).items() if isinstance(v, Component)}

    def positions(self) -> dict[str, list[float]]:
        """The position of each component (by name) in the lab frame, m, at its angles; rounded to
        the nm, so rotation noise reads 0.0 (+ 0.0: never -0.0)."""
        instr_param_dict = {p.name: p.value for p in self.instr_params}
        at_rotated_dict = place_absolute(
            self.components, instr_param_dict
        )  # name -> (position, rotation)
        return {
            name: (position.round(9) + 0.0).tolist()
            for name, (position, _rotation) in at_rotated_dict.items()
        }

    def __repr__(self):
        """A summary to read: the params, the instrument parameters, and the components in the
        order of the beam (where each sits, and its position in the lab frame; a component's own
        repr shows its values)."""
        from tabulate import tabulate  # only when printed: importing does not need it

        values = asdict(self._params)
        params = [
            (f.name, format_value(values[f.name]), f.metadata["unit"], f.metadata["comment"])
            for f in fields(self._params)
        ]
        instr_params = [
            (p.name, format_value(p.value), p.unit, p.comment) for p in self.instr_params
        ]
        positions = self.positions()
        components = []
        for name, c in self.components.items():
            where = (
                format_value(c.at),
                format_value(c.rotated),
                c.relative or "-",
                format_value(positions[name]),
            )
            components.append((name, c.component_name, *where))
        return "\n".join(
            [
                f"{type(self).__name__} {self.name!r}",
                "",
                "Params:",
                tabulate(params, ("param", "value", "unit", "comment")),
                "",
                "Instrument parameters (McStas):",
                tabulate(instr_params, ("name", "value", "unit", "comment")),
                "",
                "Components, in the order of the beam (m, deg):",
                tabulate(
                    components, ("name", "component", "at", "rotated", "relative", "position")
                ),
            ]
        )

    def __eq__(self, other):  # also makes it unhashable: its components can be changed
        if type(other) is not type(self):
            return False
        mine = (self.name, self._params, self.components)
        return mine == (other.name, other._params, other.components)
