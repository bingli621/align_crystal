"""Single-crystal diffractometer with a three-axis goniometer (McStasScript).

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.

Goniometer (nested, outermost first):
    omega : rotation about +Y
    chi   : rotation about -Z
    phi   : rotation about +X
The sample is mounted on the innermost (phi) axis, so
R_sample = R_x(phi) applied first, then R_-z(chi), then R_y(omega).
"""

import math
from pathlib import Path

from mcstasscript.interface import instr

from align_crystal.instrument.components import (
    Monitor,
    Monitor_nD,
    Single_crystal,
    Slit,
    Source_simple,
)
from align_crystal.instrument.samples import CIF_DIR

# McStas-generated files (.instr, .c, compiled binary) and simulation output go here, not in
# the project root. Created on use.
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "mcstas_output"


def _add_instrument_parameters(inst, cfg):
    """One McStas instrument parameter per instrument parameter of `cfg`, with its value (a run
    sets its own with `set_parameters`)."""
    for p in cfg.instr_params:
        inst.add_parameter(p.name, value=p.value, unit=p.unit, comment=p.comment)


def _place(inst, name, c):
    """Add component `c` as `name`: the McStas component is its class name, the position its
    at/rotated/relative."""
    rel = c.relative
    comp = inst.add_component(name, type(c).__name__, RELATIVE=rel or "ABSOLUTE")
    kw = {"RELATIVE": rel} if rel else {}
    comp.set_AT(list(c.at), **kw)
    comp.set_ROTATED(list(c.rotated), **kw)
    return comp


def _configure_source(comp, c, cfg):
    positions = cfg.positions()
    comp.radius = c.radius
    comp.dist = math.dist(positions["source"], positions[c.focus_on])  # to the focus plane
    comp.focus_xw = cfg.slit.xwidth  # the source focuses on the slit opening
    comp.focus_yh = cfg.slit.yheight
    comp.lambda0 = c.lambda0  # a number, or the name of the instrument parameter
    comp.dlambda = 0  # monochromatic
    comp.flux = c.flux


def _configure_slit(comp, c, cfg):
    comp.xwidth = c.xwidth
    comp.yheight = c.yheight


def _configure_monitor(comp, c, cfg):
    """Integrated incident intensity, twice the slit opening; the neutrons carry on."""
    comp.xwidth = 2 * cfg.slit.xwidth
    comp.yheight = 2 * cfg.slit.yheight
    comp.restore_neutron = 1


def _configure_crystal(comp, c, cfg):
    comp.xwidth, comp.yheight, comp.zdepth = c.xwidth, c.yheight, c.zdepth
    comp.mosaic = c.mosaic
    comp.order = c.order
    cif = (
        CIF_DIR / c.reflections
    )  # a CIF file of instrument/samples/, else as given (a McStas list)
    comp.reflections = f'"{cif if cif.is_file() else c.reflections}"'
    comp.recip_cell = 1
    comp.ax, comp.ay, comp.az = c.astar
    comp.bx, comp.by, comp.bz = c.bstar
    comp.cx, comp.cy, comp.cz = c.cstar


def _configure_detector(comp, c, cfg):
    """Stored as an event list with pixel ids, so mcstastox can read it (banana th/y)."""
    lo, hi = c.two_theta_range
    comp.radius = c.radius
    comp.yheight = c.yheight
    comp.options = (
        f'"banana, theta limits=[{lo} {hi}] bins={c.n_theta}, '
        f"y limits=[{-c.yheight / 2} {c.yheight / 2}] bins={c.n_y}, "
        'list all, pixel id, t"'
    )
    comp.filename = '"detector"'
    comp.nexus_bins = 1
    comp.restore_neutron = 1


# how each component sets its McStas parameters; the others (Progress_bar, Arm) have none
_CONFIGURE = {
    Source_simple: _configure_source,
    Slit: _configure_slit,
    Monitor: _configure_monitor,
    Single_crystal: _configure_crystal,
    Monitor_nD: _configure_detector,
}


def build_instrument(config, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument with the components of `config` (any `Instrument`, e.g.
    a `SingleCrystalDiffractometer`) added in their order, and its instrument parameters."""
    Path(input_path).mkdir(parents=True, exist_ok=True)
    inst = instr.McStas_instr(config.name, input_path=str(input_path))
    _add_instrument_parameters(inst, config)
    for (
        name,
        c,
    ) in config.components.items():  # in order: McStas positions are relative to earlier ones
        comp = _place(inst, name, c)
        if type(c) in _CONFIGURE:
            _CONFIGURE[type(c)](comp, c, config)
    return inst


if __name__ == "__main__":
    from align_crystal.instrument import SingleCrystalDiffractometer

    inst = build_instrument(SingleCrystalDiffractometer())
    inst.show_parameters()
    inst.show_components()
    inst.show_diagram()
    inst.write_full_instrument()  # show_instrument_file reads the file on disk: write it first
    inst.show_instrument_file(line_numbers=True)
