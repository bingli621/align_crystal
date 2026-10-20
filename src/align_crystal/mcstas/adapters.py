"""A component's McStas parameters: its fields, as they are, and what its class's adapter adds.

An adapter, `fn(c, name, inst) -> {McStas parameter: value}`, gives what follows from the
component `c` (`name` in the instrument `inst`): from its values or its references to other
components, never a number of its own. `@adapts(Xxx, uses=...)` makes it the adapter of class
`Xxx`, taking the fields `uses` names in place of passing them through. Setting a field that is
passed through raises.
"""

import math
from dataclasses import fields

from align_crystal.instrument.components import Monitor_nD, Single_crystal, Source_simple
from align_crystal.instrument.samples import CIF_DIR

PLACEMENT = {"at", "rotated", "relative"}  # the fields the builder places it by

ADAPTERS: dict[type, tuple] = {}  # by component class: (its adapter, the fields it uses)


def adapts(cls, uses=()):
    """Make the decorated function the adapter of component class `cls`."""

    def register(fn):
        ADAPTERS[cls] = (fn, set(uses))
        return fn

    return register


def mcstas_values(c, name, inst) -> dict:
    """The McStas parameters of component `c`, `name` in the instrument `inst`."""
    fn, uses = ADAPTERS.get(type(c), (lambda *_: {}, set()))
    own = {f.name: getattr(c, f.name) for f in fields(c) if f.name not in PLACEMENT | uses}
    added = fn(c, name, inst)
    if overwritten := sorted(own.keys() & added.keys()):
        raise ValueError(f"{name} ({type(c).__name__}): its adapter sets its fields {overwritten}")
    return own | added


@adapts(Source_simple, uses=("focus_on",))
def _source_simple(c, name, inst):
    """Focused at the distance of the component it focuses on."""
    positions = inst.positions()
    if c.focus_on not in positions:
        raise ValueError(f"{name}: focus_on {c.focus_on!r} is no component")
    return {"dist": math.dist(positions[name], positions[c.focus_on])}


@adapts(Single_crystal, uses=("lattice_params", "along_beam", "in_plane", "reflections"))
def _single_crystal(c, name, inst):
    """Its reciprocal vectors in the lab frame (so recip_cell must be 1); its reflections a CIF
    file of instrument/samples/ (as a full path), else as given (a McStas list)."""
    if c.recip_cell != 1:
        raise ValueError(f"{name}: recip_cell {c.recip_cell}: only 1 (reciprocal vectors) is given")
    cif = CIF_DIR / c.reflections
    vectors = {
        f"{axis}{x}": value
        for axis, vector in zip("abc", c.reciprocal_axes())
        for x, value in zip("xyz", vector)
    }
    return {"reflections": str(cif) if cif.is_file() else c.reflections, **vectors}


@adapts(Monitor_nD, uses=("theta_limits", "theta_bins", "y_bins", "options"))
def _monitor_nd(c, name, inst):
    """Its options: theta, y (over ymin to ymax, McStas's default), then its other options."""
    lo, hi = c.theta_limits
    return {
        "options": f"theta limits=[{lo} {hi}] bins={c.theta_bins}, y bins={c.y_bins}, {c.options}"
    }
