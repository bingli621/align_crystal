"""The diffractometer to and from its nested dict: what a parameters file holds, in any format.

The dict: `name`; `params`, the diffractometer's params (ei, omega, chi, phi); and one section per
component name, in the order of the beam, with its `component` (the McStas component name, e.g.
"Slit"), its parameters, where it sits: `at`, `rotated` and `relative`, and last its `position` in
the lab frame (written, never read back). A component value that an instrument parameter gives is
the parameter's name, as in McStas (`rotated: [0, omega, 0]`).

`over_default(data)` lays a dict that holds only what differs over the default diffractometer: a
value it gives wins, one it leaves out or sets to null stays as made.
"""

import copy
from dataclasses import asdict

from ..instrument import DEFAULT_PARAMS, Params, SingleCrystalDiffractometer
from ..instrument.components import COMPONENTS

# the fields of a component that say where it sits: last in its section, in this order
PLACEMENT = ("at", "rotated", "relative")
POSITION = "position"  # where it is in the lab frame: written last, for reading; never read back
SECTIONS = ("name", "params")  # the keys of the dict that are not components


def merge(base: dict, over: dict) -> dict:
    """`base` with `over` laid over it (neither is changed): a value in `over` wins, one it leaves
    out or sets to null stays as in `base`; dicts are merged key by key, a list is replaced."""
    merged = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge(merged[key], value)
        elif value is not None or key not in merged:
            merged[key] = copy.deepcopy(value)
    return merged


def to_dict(d: SingleCrystalDiffractometer) -> dict:
    """The nested dict of `d`, the one `from_dict` takes. Each section has its `component`, its
    parameters (unset optional ones left out), `at`, `rotated`, `relative`, and last its `position`
    in the lab frame (m; with the diffractometer's angles), which `from_dict` ignores."""
    positions = d.positions()
    sections = {}
    for name, c in d.components.items():
        values = asdict(c)
        placement = {k: values.pop(k) for k in PLACEMENT}
        sections[name] = {
            "component": type(c).__name__,
            **{k: v for k, v in values.items() if v is not None},
            **placement,
            POSITION: [round(x, 9) + 0.0 for x in positions[name]],  # + 0.0: no -0.0
        }
    return {"name": d.name, "params": asdict(d.params), **sections}


def from_dict(data: dict) -> SingleCrystalDiffractometer:
    """The diffractometer of the complete nested dict `data`, with the layout of params.yaml. The
    order of its sections does not matter: the diffractometer of its `params`, with the
    components of its sections (no sample if it has none)."""
    data = copy.deepcopy(data)
    d = SingleCrystalDiffractometer(params=Params(**data["params"]))
    d.name = data["name"]
    for name, c in components(data).items():
        setattr(d, name, c)
    return d


def over_default(
    data: dict, sample=None, params: Params = DEFAULT_PARAMS
) -> SingleCrystalDiffractometer:
    """The diffractometer made with `sample` and `params` (see `SingleCrystalDiffractometer`), with
    `data` (only what differs) laid over it."""
    return from_dict(merge(to_dict(SingleCrystalDiffractometer(sample, params)), data))


def components(data: dict, classes: dict = COMPONENTS) -> dict:
    """The components of `data`, keyed by name, in the order of their sections (every key but
    `SECTIONS`); each is the class its section's `component` names: `classes` maps a component name
    (e.g. "Slit") to its class."""
    made = {}
    for name, section in data.items():
        if name in SECTIONS:
            continue
        values = {k: v for k, v in section.items() if k not in ("component", POSITION)}
        made[name] = classes[section["component"]](**values)
    return made
