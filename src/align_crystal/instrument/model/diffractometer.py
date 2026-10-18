"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + sample -> detector.

`SingleCrystalDiffractometer(sample, ei, omega, chi, phi)` makes its own components (the
defaults, set in `__init__`; lengths in m, angles in deg) around the `sample`. Its params (`ei` and
the goniometer angles) are kept in one place, read with `params` and changed with `update_params`;
the instrument parameters McStas gets (`instr_params`: the wavelength of `ei`, and the angles) are
calculated from them when used. A value left None is calculated when used (the source's focus
distance, from `focus_on`).

It knows no dicts or files: io/ converts it to and from its nested dict and a YAML file. No McStas
knowledge: mcstas/builder.py builds the McStas instrument from it.
"""

import math

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
from align_crystal.instrument.params import InstrParam, with_values


class SingleCrystalDiffractometer:
    """The components, one attribute each, in the order of the beam (the name is the one a
    `relative` refers to), and its params (`params`: `ei`, `omega`, `chi`, `phi`). `components`
    gives the components as a dict by name, `instr_params` the McStas instrument parameters.

    Where a component takes a number (or a list of them, as `at` and `rotated`), it may be given
    the name of an instrument parameter instead, or an expression of them ("-chi"), as in McStas.
    """

    # set by `__init__`, in the order of the beam
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

    def __init__(
        self,
        sample: Single_crystal | None = None,
        ei: float = 14.0,
        omega: float = 0.0,
        chi: float = 0.0,
        phi: float = 0.0,
    ):
        """The default diffractometer (lengths in m, angles in deg) around `sample` (e.g.
        `la2ni7(at=[0, 0, 0], relative="gonio_phi")`; None: none), with the incident energy `ei`
        (meV) and the goniometer angles `omega`, `chi`, `phi` (deg); a run may give its own angles."""
        self._params = {"ei": ei, "omega": omega, "chi": chi, "phi": phi}
        self.name = "single_crystal_diffractometer"  # the McStas instrument name
        self.origin = Progress_bar(at=[0, 0, 0])
        self.source = Source_simple(
            radius=0.03,
            focus_on="sample_pos",  # the component the source focuses on
            dist=None,  # source -> focus plane: derived from focus_on
            flux=1.0e10,
            at=[0, 0, 0],
            relative="origin",
        )
        # opening = source focus
        self.slit = Slit(xwidth=0.01, yheight=0.01, at=[0, 0, 1.0], relative="source")
        # integrated incident intensity, 10 cm before the sample; the neutrons carry on
        self.incident_monitor = Monitor(at=[0, 0, 1.9], relative="source")
        # the beam hits the goniometer centre; it can be dumped here
        self.sample_pos = Arm(at=[0, 0, 2.0], relative="source")
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
    def params(self) -> dict:
        """A copy of the params by name: `ei` (meV), `omega`, `chi`, `phi` (deg). Changing it
        changes nothing; `update_params` does."""
        return dict(self._params)

    def update_params(self, **values):
        """Change params, e.g. `update_params(ei=25)`. Raises on a name that is not one."""
        unknown = set(values) - set(self._params)
        if unknown:
            raise ValueError(f"Unknown param(s): {', '.join(sorted(unknown))}")
        self._params.update(values)

    @property
    def wavelength(self) -> float:
        """The wavelength of `ei`, angstrom: sqrt(81.80421 / ei[meV])."""
        return math.sqrt(81.80421 / self._params["ei"])

    @property
    def instr_params(self) -> list[InstrParam]:
        """The instrument parameters (McStas instrument parameters), from the params: the
        wavelength of `ei`, and the goniometer angles."""
        p = self._params
        return [
            InstrParam("wavelength", self.wavelength, "angstrom", "neutron wavelength"),
            InstrParam("omega", p["omega"], "deg", "goniometer rotation about +Y"),
            InstrParam("chi", p["chi"], "deg", "goniometer rotation about -Z"),
            InstrParam("phi", p["phi"], "deg", "goniometer rotation about +X"),
        ]

    @property
    def components(self) -> dict[str, Component]:
        """The components by name, in the order of the beam (no sample if there is none)."""
        names = [n for n in SingleCrystalDiffractometer.__annotations__ if n != "name"]
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}

    @property
    def source_dist(self) -> float:
        """The source -> focus plane distance, m: the source's `dist`, or, if that is None, the z
        of the component it focuses on (`focus_on`, placed relative to the source)."""
        if self.source.dist is not None:
            return self.source.dist
        return self.components[self.source.focus_on].at[2]

    def instrument_param(self, **values) -> list[InstrParam]:
        """The instrument parameters of a run: `instr_params`, with `values` (McStas name -> value)
        in place of the diffractometer's."""
        return with_values(self.instr_params, **values)

    def __repr__(self):
        """Its params, one per line: "name = value"."""
        return "\n".join(
            [
                "Single crystal diffractometer with parameters:",
                *(f"{k} = {v}" for k, v in self._params.items()),
            ]
        )

    def __eq__(self, other):  # also makes it unhashable: its components can be changed
        return type(other) is type(self) and (self.name, self._params, self.components) == (
            other.name,
            other._params,
            other.components,
        )


if __name__ == "__main__":
    from align_crystal.instrument.components.sample import la2ni7

    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")

    diffractometer = SingleCrystalDiffractometer(sample)
    print(diffractometer)
    # print(diffractometer.instr_params)
    # print(diffractometer.components)
