"""The diffractometer to and from its nested dict: what a parameters file holds, in any format.

The dict: `name`; `instr_params`, the instrument parameters, name -> {value, unit, comment} (a value
null must be set by every run, or is calculated); and one section per component name, in the order
of the beam, with its `component` (the McStas component name, e.g. "Slit"), its parameters, and last
where it sits: `at`, `rotated` and `relative`. Where a value is null, the component derives it
itself. A component value that an instrument parameter gives is the parameter's name, as in McStas
(`rotated: [0, omega, 0]`).

`over_default(data)` lays a dict that holds only what differs over the default diffractometer: a
value it gives wins, one it leaves out or sets to null stays as made.
"""

import copy
from dataclasses import asdict

from ..instrument import CtrlParam, InstrParam, SingleCrystalDiffractometer
from ..instrument.components import COMPONENTS

# the fields of a component that say where it sits: last in its section, in this order
PLACEMENT = ("at", "rotated", "relative")
SECTIONS = ("name", "instr_params")  # the keys of the dict that are not components


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
    parameters (unset optional ones left out), and last `at`, `rotated`, `relative`."""
    sections = {}
    for name, c in d.components.items():
        values = asdict(c)
        placement = {k: values.pop(k) for k in PLACEMENT}
        sections[name] = {
            "component": type(c).__name__,
            **{k: v for k, v in values.items() if v is not None},
            **placement,
        }
    instr_params = {
        p.name: {"value": p.value, "unit": p.unit, "comment": p.comment} for p in d.instr_params
    }
    return {"name": d.name, "instr_params": instr_params, **sections}


def from_dict(data: dict) -> SingleCrystalDiffractometer:
    """The diffractometer of the complete nested dict `data`, with the layout of params.yaml. The
    order of its sections does not matter. Missing and unknown keys raise a ValueError."""
    data = copy.deepcopy(data)
    return SingleCrystalDiffractometer.from_parts(
        data["name"], instr_params_from_dict(data.get("instr_params") or {}), components(data)
    )


def over_default(data: dict, ctrl_params: list[CtrlParam] = ()) -> SingleCrystalDiffractometer:
    """The diffractometer made with `ctrl_params`, with `data` (only what differs) laid over it."""
    return from_dict(merge(to_dict(SingleCrystalDiffractometer(ctrl_params)), data))


def instr_params_from_dict(section: dict) -> list[InstrParam]:
    """The instrument parameters of an `instr_params` section: name -> {value, unit, comment}.
    `value` is required (null: every run sets it); `unit` and `comment` are optional."""
    params = []
    for name, entry in section.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(f"instr_params.{name} needs a value (null: every run sets it)")
        for key in set(entry) - {"value", "unit", "comment"}:
            raise ValueError(f"Unknown config key: instr_params.{name}.{key}")
        params.append(
            InstrParam(name, entry["value"], entry.get("unit", ""), entry.get("comment", ""))
        )
    return params


def components(data: dict, classes: dict = COMPONENTS) -> dict:
    """The components of `data`, keyed by name, in the order of their sections (every key but
    `SECTIONS`); each is the class its section's `component` names: `classes` maps a component name
    (e.g. "Slit") to its class. Raises on a section that is not one or has no known `component`, and
    on a missing or unknown parameter."""
    made = {}
    for name, section in data.items():
        if name in SECTIONS:
            continue
        if not isinstance(section, dict):
            raise TypeError(f"Unknown config key: {name} (not a section)")
        component_name = section.get("component")
        if component_name is None:
            raise ValueError(f"No component in the section of {name!r}")
        if component_name not in classes:
            raise ValueError(f"Unknown component {component_name!r} for {name!r}")
        values = {k: v for k, v in section.items() if k != "component"}
        try:
            made[name] = classes[component_name](**values)
        except TypeError as error:  # a missing or unknown parameter
            raise ValueError(f"Bad parameters for {name!r}: {error}") from None
    return made
