"""Builds the default diffractometer in code: the same values as params.yaml. Lengths in m, angles
in deg. A value left None is calculated: by the component itself, or by the diffractometer (the
source focus distance)."""

from ..components import (
    Arm,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from ..params import Control, ControlParam
from .diffractometer import SingleCrystalDiffractometer


def build_diffractometer(crystal: Single_crystal | None = None) -> SingleCrystalDiffractometer:
    """The default diffractometer, with `crystal` (a `Single_crystal`, e.g.
    `la2ni7(at=[0, 0, 0], relative="gonio_phi")`) as its sample, as it is; None: no sample."""
    # the control parameters (McStas instrument parameters); a value None: every run sets it
    energy_meV = Control(None, "meV", "neutron energy (monochromatic)")
    omega = Control(0.0, "deg", "goniometer rotation about +Y")
    chi = Control(0.0, "deg", "goniometer rotation about -Z")
    phi = Control(0.0, "deg", "goniometer rotation about +X")

    # the components, in the order of the beam
    origin = Progress_bar(at=[0, 0, 0])
    source = Source_simple(
        E0="energy_meV",  # the control parameter
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
    # goniometer arms, outermost first; each is rotated by a control parameter, so it can be scanned
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
        controls=ControlParam.from_controls(energy_meV=energy_meV, omega=omega, chi=chi, phi=phi),
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
