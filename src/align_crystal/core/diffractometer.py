"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + crystal -> detector.

Its components, each knowing where it sits, and its control parameters (the energy and the three
goniometer angles). Created from the nested dict of its parameters (`from_dict`), from a file
(`from_file`, its own params.yaml by default), or in code (`builder.build_diffractometer`);
`to_dict` gives the dict back. No McStas knowledge: mcstas/builder.py builds the McStas instrument
from it.
"""

import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import ClassVar, get_args

from .components import (
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
from ..samples import Sample
from .params import ControlParam, DesignParam

PLACEMENT = (
    "at",
    "rotated",
    "relative",
)  # the fields of a component that say where it sits: last in its section, in this order


def _takes_numbers(f) -> bool:
    """Whether the component field `f` holds a number (or a list), which may be a control name."""
    return any(t in (int, float, list) for t in (get_args(f.type) or (f.type,)))


@dataclass(kw_only=True)
class SingleCrystalDiffractometer:
    """The components, one field each in the order of the beam (the order they are built, each one
    knows where it sits; its field name is its name, the one that a `relative` refers to), and the
    control parameters (`controls`, the McStas instrument parameters). `components` gives them as
    a dict by name. The `sample` is optional and is not one of the design parameters: `to_dict` and
    `from_dict` leave it out.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of a control parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    PARAMS_FILE: ClassVar = Path(__file__).parent / "params.yaml"  # the default parameters

    name: str
    origin: Progress_bar
    source: Source_simple
    slit: Slit
    incident_monitor: Monitor
    sample_pos: Arm
    gonio_omega: Arm
    gonio_chi: Arm
    gonio_phi: Arm
    crystal: Single_crystal
    detector: Monitor_nD
    controls: ControlParam = field(default_factory=lambda: ControlParam({}, {}, {}))
    sample: Sample | None = None  # the crystal to simulate; None: the simulation's default

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam."""
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if isinstance(getattr(self, f.name), Component)
        }

    def __post_init__(self):
        """Derive the source focus distance: unless `dist` is given, it is the z of the component it focuses on (`focus_on`, placed
        relative to the source). Then raise if a value that is not optional is still null, if a
        control has the name of a component, and if a component uses a name that is not a control."""
        if self.source.dist is None:
            if source_focus := self.components.get(self.source.focus_on):
                self.source.dist = source_focus.at[2]
            else:
                raise ValueError(
                    f"The source focuses on {self.source.focus_on!r}, which is not a component"
                )

        for name in self.controls:
            if name in self.components:
                raise ValueError(f"The control parameter {name!r} is also a component name")
        for name, c in self.components.items():
            for f in fields(c):
                value = getattr(c, f.name)
                if value is None and f.name not in c.OPTIONAL:
                    raise ValueError(
                        f"Config value {name}.{f.name} is unresolved (null)"
                    )
                if not _takes_numbers(f):
                    continue
                for item in value if isinstance(value, list) else [value]:
                    if not isinstance(item, str):
                        continue
                    for word in re.findall(r"[A-Za-z_]\w*", item):
                        if word not in self.controls:
                            raise ValueError(
                                f"{name}.{f.name} uses {word!r}, which is not a control parameter"
                            )

    @classmethod
    def from_dict(cls, data: dict):
        """The diffractometer of the complete nested dict `data` (see `DesignParam`), with the
        layout of params.yaml. The order of its sections does not matter (the order of the beam is
        that of the fields). Missing and unknown keys raise a ValueError."""
        design = DesignParam(data)
        try:
            return cls(
                name=design["name"],
                controls=design.control_param(),
                **design.make_components(COMPONENTS),
            )
        except TypeError as error:  # a missing or unknown component
            raise ValueError(f"Bad components: {error}") from None

    @classmethod
    def from_file(cls, file=None, loader=None):
        """The diffractometer of the parameters file `file` (default: `PARAMS_FILE`), read with
        `loader`, a function from a path to the dict `from_dict` takes (default: YAML)."""
        if loader is None:
            from ..yaml_io import yaml_loader as loader  # only now: core itself knows no YAML
        return cls.from_dict(loader(file or cls.PARAMS_FILE))

    def control_param(self, **values) -> ControlParam:
        """The control parameters of a run: `controls`, with `values` (McStas name -> value) in
        place of the start values (a value still None must be set by the run, see
        `ControlParam.complete`). Raises on a name in `values` that is not a control."""
        return self.controls.replace(**values)

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
        return {"name": self.name, "controls": self.controls.to_dict(), **sections}
