"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + crystal -> detector.

Its components, each knowing where it sits, and its instrument parameters (the wavelength and the
three goniometer angles). The wavelength is calculated from the source's incident energy `ei`
(given when the instrument is made) unless a run sets it. Made in code
(`builder.build_diffractometer`, optionally with a parameters file laid over it) or from the nested
dict of its parameters (`from_dict`); `to_dict` gives the dict back. Its components are plain
attributes (`d.slit.xwidth = 0.02`): what follows from them is computed when used, and `validate`
checks the whole again. No McStas knowledge: mcstas/builder.py builds the McStas instrument from it.
"""

import re
from dataclasses import asdict, dataclass, field, fields
from typing import get_args

from ..components import (
    COMPONENTS,
    Arm,
    Component,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from ..params import DesignParam, InstrParam, InstrParams

# the fields of a component that say where it sits: last in its section, in this order
PLACEMENT = ("at", "rotated", "relative")


def _takes_numbers(f) -> bool:
    """Whether the component field `f` holds a number (or a list), which may name a parameter."""
    return any(t in (int, float, list) for t in (get_args(f.type) or (f.type,)))


def _names(value):
    """The names in `value`, a string or a list holding some: "-chi" gives chi."""
    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, str):
            yield from re.findall(r"[A-Za-z_]\w*", item)


@dataclass(kw_only=True)
class SingleCrystalDiffractometer:
    """The components, one field each in the order of the beam (the order they are built, each one
    knows where it sits; its field name is its name, the one that a `relative` refers to), and the
    instrument parameters (`instr_params`, the McStas instrument parameters; a dict of `InstrParam`
    by name is made into `InstrParams`). `components` gives the components as a dict by name.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of an instrument parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    name: str
    origin: Progress_bar
    source: Source_simple
    slit: Slit
    incident_monitor: Monitor
    sample_pos: Arm
    gonio_omega: Arm
    gonio_chi: Arm
    gonio_phi: Arm
    crystal: Single_crystal | None = None  # None: no sample
    detector: Monitor_nD
    instr_params: InstrParams | dict[str, InstrParam] = field(
        default_factory=lambda: InstrParams({}, {}, {})
    )

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam."""
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if isinstance(getattr(self, f.name), Component)
        }

    def __post_init__(self):
        if isinstance(self.instr_params, dict):
            self.instr_params = InstrParams.from_parameters(**self.instr_params)
        self.validate()

    @property
    def source_dist(self) -> float:
        """The source -> focus plane distance, m: the source's `dist`, or, if that is None, the z
        of the component it focuses on (`focus_on`, placed relative to the source)."""
        if self.source.dist is not None:
            return self.source.dist
        return self.components[self.source.focus_on].at[2]

    def validate(self):
        """Raise if the source focuses on something that is not a component, if a value that is not
        optional is null, if an instrument parameter has the name of a component, or if a component
        uses a name that is not an instrument parameter. Returns self. Run again after changing a
        component."""
        if self.source.focus_on not in self.components:
            raise ValueError(
                f"The source focuses on {self.source.focus_on!r}, which is not a component"
            )
        for name in self.instr_params:
            if name in self.components:
                raise ValueError(f"The instrument parameter {name!r} is also a component name")
        for name, c in self.components.items():
            for f in fields(c):
                value = getattr(c, f.name)
                if value is None and f.name not in c.OPTIONAL:
                    raise ValueError(f"Config value {name}.{f.name} is unresolved (null)")
                if _takes_numbers(f):
                    for word in _names(value):
                        if word not in self.instr_params:
                            raise ValueError(
                                f"{name}.{f.name} uses {word!r}, which is not an instrument parameter"
                            )
        return self

    @classmethod
    def from_dict(cls, data: dict):
        """The diffractometer of the complete nested dict `data` (see `DesignParam`), with the
        layout of params.yaml. The order of its sections does not matter (the order of the beam is
        that of the fields). Missing and unknown keys raise a ValueError."""
        design = DesignParam(data)
        try:
            return cls(
                name=design["name"],
                instr_params=design.instrument_param(),
                **design.make_components(COMPONENTS),
            )
        except TypeError as error:  # a missing or unknown component
            raise ValueError(f"Bad components: {error}") from None

    def instrument_param(self, **values) -> InstrParams:
        """The instrument parameters of a run: `instr_params`, with `values` (McStas name -> value)
        in place of the start values (a value still None must be set by the run, see
        `InstrParams.complete`); the wavelength, if not set, is calculated from the source's `ei`.
        Raises on a name in `values` that is not an instrument parameter."""
        params = self.instr_params
        if params.values.get("wavelength", 0) is None and self.source.ei is not None:
            params = params.replace(wavelength=self.source.wavelength)
        return params.replace(**values)

    def to_dict(self):
        """The nested dict `from_dict` takes. Each section has its `component`, its parameters
        (unset optional ones left out), and last `at`, `rotated`, `relative`."""
        sections = {}
        for name, c in self.components.items():
            values = asdict(c)
            placement = {k: values.pop(k) for k in PLACEMENT}
            sections[name] = {
                "component": type(c).__name__,
                **{k: v for k, v in values.items() if v is not None},
                **placement,
            }
        return {"name": self.name, "instr_params": self.instr_params.to_dict(), **sections}
