"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + sample -> detector.

`SingleCrystalDiffractometer(sample, params)` makes its own components (the defaults, set in
`__init__`; lengths in m, angles in deg) around the `sample`. Its control parameters, `Params`
(`ei` and the goniometer angles), are kept in one place: read with `params` (frozen), changed with
`update_params`. The instrument parameters McStas gets (`instr_params`: the wavelength of `ei`,
and the angles) are calculated from them when used, and so are the components' positions in the
lab frame (`positions`).

It knows no dicts or files: io/ converts it to and from its nested dict and a YAML file. No McStas
knowledge: mcstas/builder.py builds the McStas instrument from it.
"""

from dataclasses import asdict, dataclass, field, fields, replace

from align_crystal.instrument.components import (
    Arm,
    Component,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from align_crystal.instrument.geometry import place
from align_crystal.instrument.params import InstrParam
from align_crystal.instrument.utils import format_value


@dataclass(frozen=True)
class Params:
    """The control parameters of the diffractometer: what you set on it. Frozen: change them with
    `SingleCrystalDiffractometer.update_params`. Each field's `unit` is in its metadata."""

    ei: float = field(default=14.0, metadata={"unit": "meV"})  # incident energy
    omega: float = field(default=0.0, metadata={"unit": "deg"})  # goniometer rotation about +Y
    chi: float = field(default=0.0, metadata={"unit": "deg"})  # goniometer rotation about -Z
    phi: float = field(default=0.0, metadata={"unit": "deg"})  # goniometer rotation about +X


DEFAULT_PARAMS = Params()  # frozen, so one shared default is safe


class SingleCrystalDiffractometer:
    """The components, one attribute each, in the order of the beam (the name is the one a
    `relative` refers to), and its params (`params`: `ei`, `omega`, `chi`, `phi`). `components`
    gives the components as a dict by name, `instr_params` the McStas instrument parameters.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of an instrument parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    # the attributes, for type hints; `__init__` sets them, and its order is the beam's
    name: str
    origin: Progress_bar
    source: Source_simple
    slit: Slit
    incident_monitor: Monitor
    sample_pos: Arm
    gonio_omega: Arm
    gonio_chi: Arm
    gonio_phi: Arm
    sample: Single_crystal | None
    detector: Monitor_nD

    def __init__(self, sample: Single_crystal | None = None, params: Params = DEFAULT_PARAMS):
        """The default diffractometer (lengths in m, angles in deg) around `sample` (e.g.
        `la2ni7(at=[0, 0, 0], relative="gonio_phi")`; None: none), with its control parameters
        `params` (e.g. `Params(ei=25, omega=30)`; a run may give its own angles)."""
        self._params = params
        self.name = "single_crystal_diffractometer"  # the McStas instrument name
        self.origin = Progress_bar(at=[0, 0, 0])
        self.source = Source_simple(
            radius=0.03,
            focus_on="sample_pos",  # the component the source focuses on
            flux=1.0e10,
            at=[0, 0, 0],
            relative="origin",
        )
        # opening = source focus
        self.slit = Slit(xwidth=0.01, yheight=0.01, at=[0, 0, 1.0], relative="source")
        # integrated incident intensity, 10 cm before the sample; the neutrons carry on
        self.incident_monitor = Monitor(at=[0, 0, 0.9], relative="slit")
        # the beam hits the goniometer centre; it can be dumped here
        self.sample_pos = Arm(at=[0, 0, 0.1], relative="incident_monitor")
        # goniometer arms, outermost first; each is rotated by an instrument parameter
        self.gonio_omega = Arm(at=[0, 0, 0], rotated=[0, "omega", 0], relative="sample_pos")  # +Y
        self.gonio_chi = Arm(at=[0, 0, 0], rotated=[0, 0, "-chi"], relative="gonio_omega")  # -Z
        self.gonio_phi = Arm(at=[0, 0, 0], rotated=["phi", 0, 0], relative="gonio_chi")  # +X
        # the sample, in the innermost goniometer arm; None: none
        self.sample = sample
        # cylindrical ("banana") detector around the vertical axis through the sample
        self.detector = Monitor_nD(
            radius=1.0,
            yheight=0.5,
            two_theta_range=[-125.0, -5.0],  # signed: negative = right of the beam
            n_theta=1200,
            n_y=50,
            at=[0, 0, 0],
            relative="sample_pos",
        )

    @property
    def params(self) -> Params:
        """Its control parameters (frozen: `update_params` changes them)."""
        return self._params

    def update_params(self, **values):
        """Change control parameters, e.g. `update_params(ei=25)`; an unknown name raises."""
        self._params = replace(self._params, **values)

    @property
    def instr_params(self) -> list[InstrParam]:
        """The instrument parameters (McStas instrument parameters), from the params: the
        wavelength of `ei`, and the goniometer angles."""
        p = self._params
        wavelength = Source_simple.wavelength_from_ei(p.ei)
        return [
            InstrParam("wavelength", wavelength, "angstrom", "neutron wavelength"),
            InstrParam("omega", p.omega, "deg", "goniometer rotation about +Y"),
            InstrParam("chi", p.chi, "deg", "goniometer rotation about -Z"),
            InstrParam("phi", p.phi, "deg", "goniometer rotation about +X"),
        ]

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam (no sample if there is none): its
        attributes that are components, in the order `__init__` first sets them."""
        return {n: v for n, v in vars(self).items() if isinstance(v, Component)}

    def positions(self) -> dict[str, list[float]]:
        """The position of each component (by name) in the lab frame, m, at its angles."""
        angles = {p.name: p.value for p in self.instr_params}
        placed = place(self.components, angles)  # name -> (position, rotation)
        return {name: position.tolist() for name, (position, _rotation) in placed.items()}

    def __repr__(self):
        """A summary to read: the params, the instrument parameters, and the components in the
        order of the beam (where each sits, and its position in the lab frame; a component's own
        repr shows its values)."""
        from tabulate import tabulate  # only when printed: importing does not need it

        values = asdict(self._params)
        params = [
            (f.name, format_value(values[f.name]), f.metadata["unit"]) for f in fields(Params)
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
            components.append((name, type(c).__name__, *where))
        return "\n".join(
            [
                f"Single crystal diffractometer {self.name!r}",
                "",
                "Params:",
                tabulate(params, ("param", "value", "unit")),
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


if __name__ == "__main__":
    from align_crystal.instrument.samples import la2ni7

    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")

    diffractometer = SingleCrystalDiffractometer(sample)
    print(diffractometer)
    print(diffractometer.params)
    print(diffractometer.source)
    print(sample)
