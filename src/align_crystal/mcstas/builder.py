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

# McStas-generated files (.instr, .c, compiled binary) and simulation output go here, not in
# the project root. Created on use.
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "mcstas_output"


def _add_instrument_parameters(inst, cfg):
    for axis, about in (("omega", "Y"), ("chi", "-Z"), ("phi", "X")):
        inst.add_parameter(
            axis,
            value=getattr(cfg, f"gonio_{axis}").angle,
            unit="deg",
            comment=f"goniometer rotation about {about}",
        )
    inst.add_parameter(
        "wavelength",
        value=cfg.source.wavelength,
        unit="angstrom",
        comment="neutron wavelength (monochromatic)",
    )


def _name(cfg, role):
    """McStas instance name of a component: its configured `name`, else its role."""
    return getattr(cfg, role).name or role


def _place(inst, cfg, role):
    """Add component `role`: component name from cfg.<role>, position from cfg.placements[role]."""
    pl = cfg.placements[role]
    rel = _name(cfg, pl.relative) if pl.relative else None
    comp = inst.add_component(
        _name(cfg, role), getattr(cfg, role).component_name, RELATIVE=rel or "ABSOLUTE"
    )
    kw = {"RELATIVE": rel} if rel else {}
    comp.set_AT(list(pl.at), **kw)
    if pl.rotated is not None:
        comp.set_ROTATED(list(pl.rotated), **kw)
    return comp


def _add_primary(inst, cfg):
    """Source -> slit -> incident monitor."""
    s, size = cfg.source, cfg.slit1.size
    _place(inst, cfg, "origin")

    src = _place(inst, cfg, "source")
    src.radius = s.radius
    src.dist = s.dist
    src.focus_xw = size
    src.focus_yh = size
    src.lambda0 = "wavelength"
    src.dlambda = 0  # monochromatic
    src.flux = s.flux

    slit = _place(inst, cfg, "slit1")
    slit.xwidth = size
    slit.yheight = size

    # Integrated incident intensity; the neutrons carry on.
    monitor = _place(inst, cfg, "incident_monitor")
    monitor.xwidth = 2 * size
    monitor.yheight = 2 * size
    monitor.restore_neutron = 1


def _add_sample(inst, cfg, sample):
    """Sample position (beam hits the goniometer centre), three nested goniometer arms, crystal."""
    for role in ("sample_pos", "gonio_omega", "gonio_chi", "gonio_phi"):
        _place(inst, cfg, role)

    c = cfg.crystal
    xtal = _place(inst, cfg, "crystal")
    xtal.xwidth = xtal.yheight = xtal.zdepth = c.size
    xtal.mosaic = sample.mosaic
    xtal.order = c.order
    xtal.reflections = f'"{sample.reflections}"'
    xtal.recip_cell = 1
    xtal.ax, xtal.ay, xtal.az = sample.astar
    xtal.bx, xtal.by, xtal.bz = sample.bstar
    xtal.cx, xtal.cy, xtal.cz = sample.cstar


def _add_detector(inst, cfg):
    """Stored as an event list with pixel ids, so mcstastox can read it (banana th/y)."""
    d = cfg.detector
    lo, hi = d.two_theta_range
    det = _place(inst, cfg, "detector")
    det.radius = d.radius
    det.yheight = d.height
    det.options = (
        f'"banana, theta limits=[{lo} {hi}] bins={d.n_theta}, '
        f"y limits=[{-d.height / 2} {d.height / 2}] bins={d.n_y}, "
        'list all, pixel id, t"'
    )
    det.filename = '"detector"'
    det.nexus_bins = 1
    det.restore_neutron = 1


def build_instrument(config, sample=None, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument: source -> slits -> goniometer+crystal -> detector.

    `config` is a DiffractometerConfig (see instrument.load_config)."""
    sample = sample or aluminium()
    Path(input_path).mkdir(parents=True, exist_ok=True)
    inst = instr.McStas_instr(config.name, input_path=str(input_path))
    _add_instrument_parameters(inst, config)
    _add_primary(inst, config)
    _add_sample(inst, config, sample)
    _add_detector(inst, config)
    return inst


if __name__ == "__main__":
    from align_crystal.instrument import load_config

    inst = build_instrument(load_config())
    inst.show_parameters()
    inst.show_components()
    inst.show_diagram()
