"""Single-crystal diffractometer with a three-axis goniometer (McStasScript).

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.

Goniometer (nested, outermost first):
    omega : rotation about +Y
    chi   : rotation about -Z
    phi   : rotation about +X
The sample is mounted on the innermost (phi) axis, so
R_sample = R_x(phi) applied first, then R_-z(chi), then R_y(omega).
"""

from pathlib import Path

from mcstasscript.interface import instr

from align_crystal.samples import aluminium

# McStas-generated files (.instr, .c, compiled binary) go here, not in the project root
WORK_DIR = Path(__file__).resolve().parents[2] / "work"
WORK_DIR.mkdir(exist_ok=True)


def build_diffractometer(
    name="align_crystal_diffractometer",
    wavelength=2.417262,  # 14 meV
    sample=None,
    sample_size=0.005,
    source_radius=0.03,
    beam_size=0.01,  # slit opening and source focus (x and y), m
    omega=0.0,
    chi=0.0,
    phi=0.0,
    detector_radius=1.0,
    detector_height=0.5,
    two_theta_range=(-125.0, -5.0),
    n_theta=1200,
    n_y=50,
    input_path=WORK_DIR,
):
    """Return a McStasScript instrument: source -> slits -> goniometer+crystal -> detector."""
    sample = sample or aluminium()
    inst = instr.McStas_instr(name, input_path=str(input_path))

    inst.add_parameter(
        "omega", value=omega, unit="deg", comment="goniometer rotation about Y"
    )
    inst.add_parameter(
        "chi", value=chi, unit="deg", comment="goniometer rotation about -Z"
    )
    inst.add_parameter(
        "phi", value=phi, unit="deg", comment="goniometer rotation about X"
    )
    inst.add_parameter(
        "wavelength",
        value=wavelength,
        unit="angstrom",
        comment="neutron wavelength (monochromatic)",
    )

    origin = inst.add_component("origin", "Progress_bar")
    origin.set_AT([0, 0, 0])

    src = inst.add_component("source", "Source_simple", RELATIVE="origin")
    src.set_AT([0, 0, 0])
    src.radius = source_radius
    src.dist = 2.0
    src.focus_xw = beam_size
    src.focus_yh = beam_size
    src.lambda0 = "wavelength"
    src.dlambda = 0  # monochromatic
    src.flux = 1e10

    slit1 = inst.add_component("slit1", "Slit", RELATIVE="source")
    slit1.set_AT([0, 0, 1.0], RELATIVE="source")
    slit1.xwidth = beam_size
    slit1.yheight = beam_size

    # Sample position, beam hits the goniometer centre
    sample_pos = inst.add_component("sample_pos", "Arm")
    sample_pos.set_AT([0, 0, 2.0], RELATIVE="source")

    # Goniometer: three nested arms
    gonio_omega = inst.add_component("gonio_omega", "Arm")
    gonio_omega.set_AT([0, 0, 0], RELATIVE="sample_pos")
    gonio_omega.set_ROTATED([0, "omega", 0], RELATIVE="sample_pos")

    gonio_chi = inst.add_component("gonio_chi", "Arm")
    gonio_chi.set_AT([0, 0, 0], RELATIVE="gonio_omega")
    gonio_chi.set_ROTATED([0, 0, "-chi"], RELATIVE="gonio_omega")

    gonio_phi = inst.add_component("gonio_phi", "Arm")
    gonio_phi.set_AT([0, 0, 0], RELATIVE="gonio_chi")
    gonio_phi.set_ROTATED(["phi", 0, 0], RELATIVE="gonio_chi")

    xtal = inst.add_component("crystal", "Single_crystal", RELATIVE="gonio_phi")
    xtal.set_AT([0, 0, 0], RELATIVE="gonio_phi")
    xtal.xwidth = sample_size
    xtal.yheight = sample_size
    xtal.zdepth = sample_size
    xtal.mosaic = sample.mosaic
    xtal.reflections = f'"{sample.reflections}"'
    xtal.recip_cell = 1
    xtal.ax, xtal.ay, xtal.az = sample.astar
    xtal.bx, xtal.by, xtal.bz = sample.bstar
    xtal.cx, xtal.cy, xtal.cz = sample.cstar

    # Cylindrical ("banana") detector around the vertical axis through the sample, covering
    # two_theta_range (deg, signed: negative = right of the beam). It is stored as an event list
    # with pixel ids, so mcstastox can read it (it supports banana th/y).
    det = inst.add_component("detector", "Monitor_nD", RELATIVE="sample_pos")
    det.set_AT([0, 0, 0], RELATIVE="sample_pos")
    det.radius = detector_radius
    det.yheight = detector_height
    det.options = (
        f'"banana, theta limits=[{two_theta_range[0]} {two_theta_range[1]}] bins={n_theta}, '
        f"y limits=[{-detector_height / 2} {detector_height / 2}] bins={n_y}, "
        'list all, pixel id, t"'
    )
    det.filename = '"detector"'
    det.nexus_bins = 1
    det.restore_neutron = 1

    return inst


if __name__ == "__main__":
    inst = build_diffractometer()
    inst.show_parameters()
    inst.show_components()
