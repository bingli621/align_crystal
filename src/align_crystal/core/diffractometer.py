"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + crystal -> detector.

Its components, each knowing where it sits, and its control parameters (the energy and the three
goniometer angles). Created from the nested dict of its parameters (`from_dict`), from a file
(`from_file`, its own params.yaml by default), or in code (`from_parameters`, the same defaults);
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
    a dict by name.

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

    @classmethod
    def from_parameters(cls):
        """The diffractometer with the default parameters, its components made directly here, one
        by one, in the order of the beam (the same values as params.yaml). Lengths in m, angles in
        deg. A value left None is calculated: by the component itself, or in `__post_init__` (the
        source focus distance)."""
        # the control parameters (McStas instrument parameters); a value None: every run sets it
        controls = {
            "energy_meV": {"value": None, "unit": "meV", "comment": "neutron energy (monochromatic)"},
            "omega": {"value": 0.0, "unit": "deg", "comment": "goniometer rotation about +Y"},
            "chi": {"value": 0.0, "unit": "deg", "comment": "goniometer rotation about -Z"},
            "phi": {"value": 0.0, "unit": "deg", "comment": "goniometer rotation about +X"},
        }
        return cls(
            name="align_crystal_diffractometer",
            controls=ControlParam.from_dict(controls),
            origin=Progress_bar(at=[0, 0, 0]),
            source=Source_simple(
                energy_meV="energy_meV",  # the control parameter
                radius=0.03,
                focus_on="sample_pos",  # the component the source focuses on
                dist=None,  # source -> focus plane: derived from focus_on
                flux=1.0e10,
                at=[0, 0, 0],
                relative="origin",
            ),
            slit=Slit(size=0.01, at=[0, 0, 1.0], relative="source"),  # opening = source focus
            # integrated incident intensity, 10 cm before the sample; the neutrons carry on
            incident_monitor=Monitor(at=[0, 0, 1.9], relative="source"),
            # the beam hits the goniometer centre; it can be dumped here
            sample_pos=Arm(at=[0, 0, 2.0], relative="source"),
            # goniometer arms, outermost first; each is rotated by a control parameter (omega, chi,
            # phi), so it can be scanned
            gonio_omega=Arm(at=[0, 0, 0], rotated=[0, "omega", 0], relative="sample_pos"),  # +Y
            gonio_chi=Arm(at=[0, 0, 0], rotated=[0, 0, "-chi"], relative="gonio_omega"),  # -Z
            gonio_phi=Arm(at=[0, 0, 0], rotated=["phi", 0, 0], relative="gonio_chi"),  # +X
            crystal=Single_crystal(
                size=0.005,  # cube edge
                order=1,  # single scattering only (no multiple scattering): much faster
                at=[0, 0, 0],
                relative="gonio_phi",
            ),
            # cylindrical ("banana") detector around the vertical axis through the sample
            detector=Monitor_nD(
                radius=1.0,
                height=0.5,
                two_theta_range=[-125.0, -5.0],  # signed: negative = right of the beam
                n_theta=1200,
                n_y=50,
                at=[0, 0, 0],
                relative="sample_pos",
            ),
        )

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
