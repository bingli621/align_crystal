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

from align_crystal.instrument.components import (
    Monitor,
    Monitor_nD,
    Single_crystal,
    Slit,
    Source_simple,
)
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
    """Add component `role`: the McStas component is its class name, the position its
    at/rotated/relative."""
    c = getattr(cfg, role)
    rel = _name(cfg, c.relative) if c.relative else None
    comp = inst.add_component(_name(cfg, role), type(c).__name__, RELATIVE=rel or "ABSOLUTE")
    kw = {"RELATIVE": rel} if rel else {}
    comp.set_AT(list(c.at), **kw)
    if c.rotated is not None:
        comp.set_ROTATED(list(c.rotated), **kw)
    return comp


def _configure_source(comp, c, cfg, sample):
    size = cfg.slit1.size  # the source focuses on the slit opening
    comp.radius = c.radius
    comp.dist = c.dist
    comp.focus_xw = size
    comp.focus_yh = size
    comp.lambda0 = "wavelength"
    comp.dlambda = 0  # monochromatic
    comp.flux = c.flux


def _configure_slit(comp, c, cfg, sample):
    comp.xwidth = c.size
    comp.yheight = c.size


def _configure_monitor(comp, c, cfg, sample):
    """Integrated incident intensity, twice the slit opening; the neutrons carry on."""
    comp.xwidth = 2 * cfg.slit1.size
    comp.yheight = 2 * cfg.slit1.size
    comp.restore_neutron = 1


def _configure_crystal(comp, c, cfg, sample):
    comp.xwidth = comp.yheight = comp.zdepth = c.size
    comp.mosaic = sample.mosaic
    comp.order = c.order
    comp.reflections = f'"{sample.reflections}"'
    comp.recip_cell = 1
    comp.ax, comp.ay, comp.az = sample.astar
    comp.bx, comp.by, comp.bz = sample.bstar
    comp.cx, comp.cy, comp.cz = sample.cstar


def _configure_detector(comp, c, cfg, sample):
    """Stored as an event list with pixel ids, so mcstastox can read it (banana th/y)."""
    lo, hi = c.two_theta_range
    comp.radius = c.radius
    comp.yheight = c.height
    comp.options = (
        f'"banana, theta limits=[{lo} {hi}] bins={c.n_theta}, '
        f"y limits=[{-c.height / 2} {c.height / 2}] bins={c.n_y}, "
        'list all, pixel id, t"'
    )
    comp.filename = '"detector"'
    comp.nexus_bins = 1
    comp.restore_neutron = 1


# how each kind of component sets its McStas parameters; the others (Progress_bar, Arm) have none
_CONFIGURE = {
    Source_simple: _configure_source,
    Slit: _configure_slit,
    Monitor: _configure_monitor,
    Single_crystal: _configure_crystal,
    Monitor_nD: _configure_detector,
}


def build_instrument(config, sample=None, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument with the components of `config` (an Instrument, see
    file_io.load_config) added in their order."""
    sample = sample or aluminium()
    Path(input_path).mkdir(parents=True, exist_ok=True)
    inst = instr.McStas_instr(config.name, input_path=str(input_path))
    _add_instrument_parameters(inst, config)
    for role, c in config.components.items():  # in order: McStas positions are relative to earlier ones
        comp = _place(inst, config, role)
        if type(c) in _CONFIGURE:
            _CONFIGURE[type(c)](comp, c, config, sample)
    return inst


if __name__ == "__main__":
    from align_crystal.file_io import load_config

    inst = build_instrument(load_config())
    inst.show_parameters()
    inst.show_components()
    inst.show_diagram()
