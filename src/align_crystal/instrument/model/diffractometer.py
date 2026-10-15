"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + crystal -> detector.

`SingleCrystalDiffractometer(ctrl_params)` makes its own components (`_default`; lengths in m,
angles in deg) from a list of `CtrlParam` (`CTRL_PARAMS`: the sample `crystal` and the incident
energy `ei`). Its instrument parameters (the wavelength and the goniometer angles) are declared
without values: the wavelength is calculated from `ei`, the angles are given by each run. A value
left None is calculated when used (the source's focus distance, from `focus_on`).

It knows no dicts or files: io/ converts it to and from its nested dict and a YAML file. No McStas
knowledge: mcstas/builder.py builds the McStas instrument from it.
"""

import re
from dataclasses import fields
from typing import get_args

from ..components import (
    Arm,
    Component,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from ..params import CtrlParam, InstrParam, with_values

NAME = "align_crystal_diffractometer"  # the McStas instrument name

# the components by name, in the order of the beam, with their class; the crystal may be None
LAYOUT = {
    "origin": Progress_bar,
    "source": Source_simple,
    "slit": Slit,
    "incident_monitor": Monitor,
    "sample_pos": Arm,
    "gonio_omega": Arm,
    "gonio_chi": Arm,
    "gonio_phi": Arm,
    "crystal": Single_crystal,
    "detector": Monitor_nD,
}
OPTIONAL_COMPONENTS = ("crystal",)

# the control parameters it takes (one left out is None): the sample, a Single_crystal in the
# innermost goniometer arm; the incident energy, meV, which the source turns into the wavelength
CTRL_PARAMS = ("crystal", "ei")


def _ctrl_values(ctrl_params) -> dict:
    """The values of the control parameters by name (None for one left out). Raises on a name that
    is not in `CTRL_PARAMS`, or that is given twice."""
    values = {}
    for p in ctrl_params:
        if p.name not in CTRL_PARAMS:
            raise ValueError(
                f"Unknown control parameter {p.name!r}; known: {', '.join(CTRL_PARAMS)}"
            )
        if p.name in values:
            raise ValueError(f"The control parameter {p.name!r} is given twice")
        values[p.name] = p.value
    return dict.fromkeys(CTRL_PARAMS) | values


def _default(crystal, ei):
    """The instrument parameters and the components (by name) of the diffractometer."""
    # the instrument parameters (McStas instrument parameters), declared without values: the
    # wavelength is calculated from the source's ei, the angles are given by each run
    instr_params = [
        InstrParam("wavelength", None, "angstrom", "neutron wavelength"),
        InstrParam("omega", None, "deg", "goniometer rotation about +Y"),
        InstrParam("chi", None, "deg", "goniometer rotation about -Z"),
        InstrParam("phi", None, "deg", "goniometer rotation about +X"),
    ]
    components = {
        "origin": Progress_bar(at=[0, 0, 0]),
        "source": Source_simple(
            ei=ei,  # the source converts it to a wavelength
            radius=0.03,
            focus_on="sample_pos",  # the component the source focuses on
            dist=None,  # source -> focus plane: derived from focus_on
            flux=1.0e10,
            at=[0, 0, 0],
            relative="origin",
        ),
        # opening = source focus
        "slit": Slit(xwidth=0.01, yheight=0.01, at=[0, 0, 1.0], relative="source"),
        # integrated incident intensity, 10 cm before the sample; the neutrons carry on
        "incident_monitor": Monitor(at=[0, 0, 1.9], relative="source"),
        # the beam hits the goniometer centre; it can be dumped here
        "sample_pos": Arm(at=[0, 0, 2.0], relative="source"),
        # goniometer arms, outermost first; each is rotated by an instrument parameter
        "gonio_omega": Arm(at=[0, 0, 0], rotated=[0, "omega", 0], relative="sample_pos"),  # +Y
        "gonio_chi": Arm(at=[0, 0, 0], rotated=[0, 0, "-chi"], relative="gonio_omega"),  # -Z
        "gonio_phi": Arm(at=[0, 0, 0], rotated=["phi", 0, 0], relative="gonio_chi"),  # +X
        "crystal": crystal,  # the sample, in the innermost goniometer arm; None: none
        # cylindrical ("banana") detector around the vertical axis through the sample
        "detector": Monitor_nD(
            radius=1.0,
            yheight=0.5,
            two_theta_range=[-125.0, -5.0],  # signed: negative = right of the beam
            n_theta=1200,
            n_y=50,
            at=[0, 0, 0],
            relative="sample_pos",
        ),
    }
    return instr_params, components


def _uses(c):
    """The names component `c` uses in place of numbers, as (field, name): "-chi" gives chi."""
    for f in fields(c):
        if not any(t in (int, float, list) for t in (get_args(f.type) or (f.type,))):
            continue  # not a number field
        value = getattr(c, f.name)
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str):
                for word in re.findall(r"[A-Za-z_]\w*", item):
                    yield f.name, word


class SingleCrystalDiffractometer:
    """The components, one attribute each, named as in `LAYOUT` (the order of the beam; the name
    is the one a `relative` refers to), and the instrument parameters (`instr_params`, a list of
    `InstrParam`). `components` gives the components as a dict by name.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of an instrument parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    # set by `_set`
    name: str
    instr_params: list[InstrParam]
    origin: Progress_bar
    source: Source_simple
    slit: Slit
    incident_monitor: Monitor
    sample_pos: Arm
    gonio_omega: Arm
    gonio_chi: Arm
    gonio_phi: Arm
    crystal: Single_crystal | None
    detector: Monitor_nD

    def __init__(self, ctrl_params: list[CtrlParam] = ()):
        """The diffractometer made with `ctrl_params`, a list of `CtrlParam` (see `CTRL_PARAMS`),
        e.g. `[CtrlParam("crystal", la2ni7(at=[0, 0, 0], relative="gonio_phi")),
        CtrlParam("ei", 14, "meV")]`; one left out is None (no sample; no energy)."""
        self._set(NAME, *_default(**_ctrl_values(ctrl_params)))

    @classmethod
    def from_parts(cls, name: str, instr_params: list[InstrParam], components: dict):
        """The diffractometer of the given parts: its McStas name, instrument parameters and
        components by name (any order; the crystal may be left out). Raises on a missing, unknown
        or wrong component."""
        d = cls.__new__(cls)
        d._set(name, instr_params, components)
        return d

    def _set(self, name, instr_params, components):
        """Set the name, the instrument parameters and the components (by name), and validate."""
        unknown = [n for n in components if n not in LAYOUT]
        if unknown:
            raise ValueError(f"Unknown component(s): {', '.join(unknown)}")
        for n, cls in LAYOUT.items():
            c = components.get(n)
            if c is None and n not in OPTIONAL_COMPONENTS:
                raise ValueError(f"Missing component: {n}")
            if c is not None and not isinstance(c, cls):
                raise ValueError(f"{n} must be a {cls.__name__}, not {type(c).__name__}")
        self.name = name
        self.instr_params = instr_params
        for n in LAYOUT:
            setattr(self, n, components.get(n))
        self.validate()

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam (no crystal if there is none)."""
        return {n: getattr(self, n) for n in LAYOUT if getattr(self, n) is not None}

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
        names = {p.name for p in self.instr_params}
        for name in names & set(self.components):
            raise ValueError(f"The instrument parameter {name!r} is also a component name")
        for name, c in self.components.items():
            for f in fields(c):
                if getattr(c, f.name) is None and f.name not in c.OPTIONAL:
                    raise ValueError(f"Config value {name}.{f.name} is unresolved (null)")
            for field_name, word in _uses(c):
                if word not in names:
                    raise ValueError(
                        f"{name}.{field_name} uses {word!r}, which is not an instrument parameter"
                    )
        return self

    def params_used(self, until: str | None = None) -> set[str]:
        """The instrument parameters the components use, up to and including the component
        `until` (None: all of them). A run that stops there needs no others."""
        used = set()
        for name, c in self.components.items():
            used.update(word for _, word in _uses(c))
            if name == until:
                break
        return used & {p.name for p in self.instr_params}

    def instrument_param(self, **values) -> list[InstrParam]:
        """The instrument parameters of a run: `instr_params`, with `values` (McStas name -> value)
        in place of the declared ones (a value still None must be set by the run, see
        `complete_values`); the wavelength, if not set, is calculated from the source's `ei`.
        Raises on a name in `values` that is not an instrument parameter."""
        calculated = {
            p.name: self.source.wavelength
            for p in self.instr_params
            if p.name == "wavelength" and p.value is None and self.source.ei is not None
        }
        return with_values(self.instr_params, **(calculated | values))

    def __eq__(self, other):  # also makes it unhashable: its components can be changed
        return type(other) is type(self) and (self.name, self.instr_params, self.components) == (
            other.name,
            other.instr_params,
            other.components,
        )
