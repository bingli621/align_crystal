"""Builds the default diffractometer in code: the entry point. Lengths in m, angles in deg. A value
left None is calculated when used (the source focus distance, from `focus_on`).

`params.yaml` next to it is this diffractometer saved, as a reference of how a parameters file
looks: `build_diffractometer(file=...)` lays such a file over the one made here, so a file need hold
only what differs (a value it gives wins; one it leaves out, or sets to null, stays as built here).
"""

from pathlib import Path

from ..components import (
    Arm,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from ..params import ControlParam, InstrumentParam, InstrumentParameter, merge
from .diffractometer import SingleCrystalDiffractometer

PARAMS_FILE = Path(__file__).parent / "params.yaml"  # this diffractometer saved: a reference


def build_diffractometer(
    crystal: Single_crystal | None = None,
    control: ControlParam | None = None,
    file=None,
    loader=None,
) -> SingleCrystalDiffractometer:
    """The default diffractometer, with `crystal` (a `Single_crystal`, e.g.
    `la2ni7(at=[0, 0, 0], relative="gonio_phi")`) as its sample; None: no sample. `control` (a `ControlParam`, e.g. `ControlParam(ei=14)`) is what is
    given when the instrument is made: the source takes its incident energy `ei` (meV) and turns it
    into the wavelength instrument parameter McStas gets (a file may give `ei` too, and wins). With a parameters
    `file`, read with `loader` (a function from a path to a dict; default: YAML), the file is laid
    over it (see the top of this file), and the result is made from the merged dict."""
    d = _build(crystal, control or ControlParam())
    if file is None:
        return d
    if loader is None:
        from ...yaml_io import yaml_loader as loader  # only now: instrument itself knows no YAML
    return SingleCrystalDiffractometer.from_dict(merge(d.to_dict(), loader(file)))


def _build(crystal, control):
    # the instrument parameters (McStas instrument parameters), set by each run; the wavelength is
    # calculated from the source's ei when used, unless a run (or the file) sets it
    wavelength = InstrumentParameter(None, "angstrom", "neutron wavelength")
    omega = InstrumentParameter(0.0, "deg", "goniometer rotation about +Y")
    chi = InstrumentParameter(0.0, "deg", "goniometer rotation about -Z")
    phi = InstrumentParameter(0.0, "deg", "goniometer rotation about +X")

    # the components, in the order of the beam
    origin = Progress_bar(at=[0, 0, 0])
    source = Source_simple(
        ei=control.ei,  # the source converts it to a wavelength
        radius=0.03,
        focus_on="sample_pos",  # the component the source focuses on
        dist=None,  # source -> focus plane: derived from focus_on
        flux=1.0e10,
        at=[0, 0, 0],
        relative="origin",
    )
    slit = Slit(
        xwidth=0.01, yheight=0.01, at=[0, 0, 1.0], relative="source"
    )  # opening = source focus
    # integrated incident intensity, 10 cm before the sample; the neutrons carry on
    incident_monitor = Monitor(at=[0, 0, 1.9], relative="source")
    # the beam hits the goniometer centre; it can be dumped here
    sample_pos = Arm(at=[0, 0, 2.0], relative="source")
    # goniometer arms, outermost first; each is rotated by an instrument parameter, so it can be scanned
    gonio_omega = Arm(at=[0, 0, 0], rotated=[0, "omega", 0], relative="sample_pos")  # about +Y
    gonio_chi = Arm(at=[0, 0, 0], rotated=[0, 0, "-chi"], relative="gonio_omega")  # about -Z
    gonio_phi = Arm(at=[0, 0, 0], rotated=["phi", 0, 0], relative="gonio_chi")  # about +X
    # cylindrical ("banana") detector around the vertical axis through the sample
    detector = Monitor_nD(
        radius=1.0,
        yheight=0.5,
        two_theta_range=[-125.0, -5.0],  # signed: negative = right of the beam
        n_theta=1200,
        n_y=50,
        at=[0, 0, 0],
        relative="sample_pos",
    )

    return SingleCrystalDiffractometer(
        name="align_crystal_diffractometer",
        instrument_params=InstrumentParam.from_parameters(
            wavelength=wavelength, omega=omega, chi=chi, phi=phi
        ),
        origin=origin,
        source=source,
        slit=slit,
        incident_monitor=incident_monitor,
        sample_pos=sample_pos,
        gonio_omega=gonio_omega,
        gonio_chi=gonio_chi,
        gonio_phi=gonio_phi,
        crystal=crystal,  # the sample, in the innermost goniometer arm; None: none
        detector=detector,
    )
