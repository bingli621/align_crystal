"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + sample -> detector.

`SingleCrystalDiffractometer(sample, params)`, an `Instrument` (base.py: what every
instrument shares), makes its own components (the defaults, set in `__init__`; lengths in m, angles
in deg) around the `sample`. Its control parameters are `Params` (params.py: `ei` and the
goniometer angles); the instrument parameters McStas gets (`instr_params`: the wavelength of `ei`,
and the angles) are calculated from them when used.

It knows no dicts or files: io/ converts it to and from its nested dict and a YAML file (which
names it `SingleCrystalDiffractometer`). No McStas knowledge: mcstas/builder.py builds the McStas
instrument from it.
"""

from align_crystal.instrument.base import Instrument
from align_crystal.instrument.components import (
    Arm,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from align_crystal.instrument.params import DEFAULT_PARAMS, InstrParam, Params


class SingleCrystalDiffractometer(Instrument):
    """The single-crystal diffractometer (see `Instrument`): its components, and its params
    (`Params`: `ei`, `omega`, `chi`, `phi`), from which follow its instrument parameters."""

    params_class = Params
    name = "single_crystal_diffractometer"  # the McStas instrument name

    # the components, for type hints; `__init__` sets them, and its order is the beam's
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
        super().__init__(params)
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


if __name__ == "__main__":
    from align_crystal.instrument.samples import la2ni7

    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")

    diffractometer = SingleCrystalDiffractometer(sample)
    print(diffractometer)
    print(diffractometer.params)
    print(diffractometer.source)
    print(sample)
