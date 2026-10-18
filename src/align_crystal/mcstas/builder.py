"""Build the McStas instrument (McStasScript) of a `SingleCrystalDiffractometer`.

Its components are added one by one, in the order of the beam (McStas positions are relative to
earlier ones), each as the McStas component of its class name, at its `at`/`rotated`/`relative`,
with its McStas parameters set from its values.

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.
"""

import math
from pathlib import Path

from mcstasscript.interface import instr

from align_crystal.instrument.samples import CIF_DIR

# McStas-generated files (.instr, .c, compiled binary) and simulation output go here, not in
# the project root. Created on use.
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "mcstas_output"


def _add(inst, name, c):
    """Add component `c` as `name`: the McStas component is its class name, the position its
    at/rotated/relative."""
    rel = c.relative
    comp = inst.add_component(name, type(c).__name__, RELATIVE=rel or "ABSOLUTE")
    kw = {"RELATIVE": rel} if rel else {}
    comp.set_AT(list(c.at), **kw)
    comp.set_ROTATED(list(c.rotated), **kw)
    return comp


def build_instrument(d, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument of the diffractometer `d`: its instrument parameters and
    its components."""
    Path(input_path).mkdir(parents=True, exist_ok=True)
    inst = instr.McStas_instr(d.name, input_path=str(input_path))
    # a run sets its own values with `set_parameters`
    for p in d.instr_params:
        inst.add_parameter(p.name, value=p.value, unit=p.unit, comment=p.comment)
    positions = d.positions()

    _add(inst, "origin", d.origin)

    source = _add(inst, "source", d.source)
    source.radius = d.source.radius
    # to the focus plane
    source.dist = math.dist(positions["source"], positions[d.source.focus_on])
    source.focus_xw = d.slit.xwidth  # the source focuses on the slit opening
    source.focus_yh = d.slit.yheight
    source.lambda0 = d.source.lambda0  # a number, or the name of the instrument parameter
    source.dlambda = 0  # monochromatic
    source.flux = d.source.flux

    slit = _add(inst, "slit", d.slit)
    slit.xwidth = d.slit.xwidth
    slit.yheight = d.slit.yheight

    # integrated incident intensity, twice the slit opening; the neutrons carry on
    monitor = _add(inst, "incident_monitor", d.incident_monitor)
    monitor.xwidth = 2 * d.slit.xwidth
    monitor.yheight = 2 * d.slit.yheight
    monitor.restore_neutron = 1

    _add(inst, "sample_pos", d.sample_pos)
    _add(inst, "gonio_omega", d.gonio_omega)
    _add(inst, "gonio_chi", d.gonio_chi)
    _add(inst, "gonio_phi", d.gonio_phi)

    if d.sample is not None:
        s = d.sample
        crystal = _add(inst, "sample", s)
        crystal.xwidth, crystal.yheight, crystal.zdepth = s.xwidth, s.yheight, s.zdepth
        crystal.mosaic = s.mosaic
        crystal.order = s.order
        # a CIF file of instrument/samples/, else as given (a McStas list)
        cif = CIF_DIR / s.reflections
        crystal.reflections = f'"{cif if cif.is_file() else s.reflections}"'
        crystal.recip_cell = 1
        crystal.ax, crystal.ay, crystal.az = s.astar
        crystal.bx, crystal.by, crystal.bz = s.bstar
        crystal.cx, crystal.cy, crystal.cz = s.cstar

    # an event list with pixel ids, so mcstastox can read it (banana th/y)
    det = d.detector
    detector = _add(inst, "detector", det)
    lo, hi = det.two_theta_range
    detector.radius = det.radius
    detector.yheight = det.yheight
    detector.options = (
        f'"banana, theta limits=[{lo} {hi}] bins={det.n_theta}, '
        f"y limits=[{-det.yheight / 2} {det.yheight / 2}] bins={det.n_y}, "
        'list all, pixel id, t"'
    )
    detector.filename = '"detector"'
    detector.nexus_bins = 1
    detector.restore_neutron = 1
    return inst


if __name__ == "__main__":
    from align_crystal.instrument import SingleCrystalDiffractometer, la2ni7

    # the sample, in the innermost goniometer arm
    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")
    inst = build_instrument(SingleCrystalDiffractometer(sample))
    inst.show_parameters()
    inst.show_components()
    inst.show_diagram()
    inst.write_full_instrument()  # show_instrument_file reads the file on disk: write it first
    inst.show_instrument_file(line_numbers=True)
