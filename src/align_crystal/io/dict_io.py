"""An instrument to and from its nested dict: what a parameters file holds, in any format.

Any `Instrument` (instrument/base.py): the dict names its class (`instrument`, a key of
INSTRUMENTS), its params are those of the class's `params_class`, its components its own. Every
dict, complete or of overrides, must name a class of INSTRUMENTS: there is no default, and a
missing or unknown one raises ValueError. The dict, here of the diffractometer, in the layout of
params.yaml:

    instrument: SingleCrystalDiffractometer   # the class: a key of INSTRUMENTS
    name: single_crystal_diffractometer
    params:                   # each param: its value, unit and comment (its field's metadata)
      ei: {value: 14.0, unit: meV, comment: incident energy}
      ...
    slit:                     # one section per component, in the order of the beam
      component: Slit         # the McStas component (the class of the same name)
      xwidth: 0.01            # its own parameters
      yheight: 0.01
      at: [0, 0, 1.0]         # where it sits: McStas AT, ROTATED, RELATIVE
      rotated: [0, 0, 0]
      relative: source
      position: [0.0, 0.0, 1.0]   # in the lab frame: written for reading, never read back
    ...

A param's unit, if given, must be its unit in the code; its comment is only for reading; a bare
number stands for its value (`ei: 25` is `ei: {value: 25}`). A component value that an instrument
parameter gives is the parameter's name, as in McStas (`rotated: [0, omega, 0]`).

What a dict gets wrong raises ValueError, saying where: `instrument: ...`, `params.ei: ...`,
`slit: ...` (an unknown or missing instrument class, an unknown param, unit, component class or
component parameter).

to_dict(instrument)                  the complete dict of an instrument
from_dict(data)                      the instrument of a complete dict, of the class it names
from_overrides(overrides, **kwargs)  the default instrument of the class `overrides` names (made
                                     with `kwargs`), with `overrides`, only what differs, laid over
                                     it: what a parameters file holds
merge(defaults, overrides)           how a dict is laid over another
"""

import copy
from dataclasses import asdict, fields

from ..instrument import INSTRUMENTS, Instrument
from ..instrument.components import COMPONENTS


def to_dict(instrument: Instrument) -> dict:
    """The complete nested dict of `instrument`, the one `from_dict` takes: its class
    (`instrument`), its `name`, its `params` and one section per component (see
    `_components_to_dict`)."""
    return {
        "instrument": type(instrument).__name__,
        "name": instrument.name,
        "params": _params_to_dict(instrument.params),
        **_components_to_dict(instrument),
    }


def from_dict(data: dict) -> Instrument:
    """The instrument of the complete nested dict `data` (as `to_dict` gives), of the class its
    `instrument` names (see `_instrument_class`). The order of its sections does not matter: the
    instrument is made with its `params` alone, and each section then replaces the component of
    its name, in that component's place in the beam (a component the class leaves at None, as the
    diffractometer's sample with none, has its place kept)."""
    instrument_class = _instrument_class(data)
    data = copy.deepcopy(data)  # the components get its lists: not shared with the caller
    params = _params_from_dict(data["params"], instrument_class.params_class)
    instrument = instrument_class(params=params)
    instrument.name = data["name"]
    for name, component in _components_from_dict(data).items():
        setattr(instrument, name, component)  # replaces the default one, in its place in the beam
    return instrument


def from_overrides(overrides: dict, **kwargs) -> Instrument:
    """The default instrument of the class `overrides` names (see `_instrument_class`), made with
    `kwargs` (for the diffractometer: `sample`, `params`), with `overrides` laid over its dict
    (`merge`): a value in `overrides` wins; one it leaves out or sets to None keeps the default.
    `overrides` names the instrument and holds only what differs, e.g.
    `{"instrument": "SingleCrystalDiffractometer", "params": {"omega": 30}}`; `from_dict` takes a
    complete dict instead."""
    instrument_class = _instrument_class(overrides)
    defaults = to_dict(instrument_class(**kwargs))  # names the class: from_dict follows it
    return from_dict(merge(defaults, overrides))


def merge(defaults: dict, overrides: dict) -> dict:
    """A copy of `defaults` with `overrides` laid over it; neither is changed. For each key of
    `overrides`:

    - a dict over a dict: merged the same way, key by key;
    - None (null in a file): the default is kept (None is stored only for a key `defaults` lacks);
    - anything else, a list included: replaces the default whole.

    A key that `overrides` leaves out keeps its default."""
    merged = copy.deepcopy(defaults)
    for key, override in overrides.items():
        default = merged.get(key)
        if isinstance(override, dict) and isinstance(default, dict):
            merged[key] = merge(default, override)
        elif override is not None or key not in merged:
            merged[key] = copy.deepcopy(override)
    return merged


def _instrument_class(data: dict) -> type[Instrument]:
    """The class that `data`'s `instrument` names: a key of INSTRUMENTS. Raise ValueError if it
    names none, or one not there."""
    named = data.get("instrument")
    if named not in INSTRUMENTS:
        raise ValueError(f"instrument: {named!r} is no instrument (known: {sorted(INSTRUMENTS)})")
    return INSTRUMENTS[named]


# the params section


def _params_to_dict(params) -> dict:
    """Each param of `params` (a dataclass) as its `value`, `unit` and `comment`."""
    return {
        f.name: {
            "value": getattr(params, f.name),
            "unit": f.metadata["unit"],
            "comment": f.metadata["comment"],
        }
        for f in fields(params)
    }


def _params_from_dict(section: dict, params_class: type):
    """The `params_class` of the params `section` (as `_params_to_dict` gives, or a bare number for
    a value). Raise ValueError if `section` names a param that `params_class` lacks, or if a
    param's unit is not its unit in the code; a comment is not read."""
    unknown = set(section) - {f.name for f in fields(params_class)}
    if unknown:
        raise ValueError(f"params: no such param {sorted(unknown)}")
    values = {}
    for f in fields(params_class):
        if f.name not in section:
            continue
        entry = section[f.name]
        if not isinstance(entry, dict):
            entry = {"value": entry}
        unit = entry.get("unit")
        if unit is not None and unit != f.metadata["unit"]:
            raise ValueError(f"params.{f.name}: unit {unit!r}, but it is {f.metadata['unit']!r}")
        values[f.name] = entry["value"]
    return params_class(**values)


# the component sections


def _components_to_dict(instrument: Instrument) -> dict:
    """One section per component of `instrument`, keyed by name, in the order of the beam: its
    `component`, its parameters (unset optional ones left out), `at`, `rotated`, `relative`, and
    last its `position` in the lab frame (m; with the instrument's params), which
    `_components_from_dict` ignores.

    The order is changed on purpose: a component's dataclass fields start with `at`, `rotated` and
    `relative` (from `Component`, its base), but here they come after its own parameters, so a
    section reads as params.yaml does: what the component is, then where it sits. Only for
    reading: `from_dict` does not depend on the order."""
    positions = instrument.positions()
    sections = {}
    for name, component in instrument.components.items():
        values = asdict(component)
        placement = {key: values.pop(key) for key in ("at", "rotated", "relative")}  # moved last
        sections[name] = {
            "component": component.component_name,
            **{key: value for key, value in values.items() if value is not None},
            **placement,
            "position": positions[name],
        }
    return sections


def _components_from_dict(data: dict, component_classes: dict = COMPONENTS) -> dict:
    """The components of `data`, keyed by name, in the order of their sections (every key but
    `instrument`, `name` and `params`); each is the class its section's `component` names:
    `component_classes` maps a component name (e.g. "Slit") to its class. Raise ValueError if a
    section names no such class, or gives a parameter the class does not take."""
    built = {}
    for name, section in data.items():
        if name in ("instrument", "name", "params"):  # the keys that are not components
            continue
        kwargs = {
            key: value for key, value in section.items() if key not in ("component", "position")
        }
        component_class = component_classes.get(section.get("component"))
        if component_class is None:
            raise ValueError(
                f"{name}: no such component {section.get('component')!r}"
                f" (known: {sorted(component_classes)})"
            )
        try:
            built[name] = component_class(**kwargs)
        except TypeError as error:  # a parameter the class does not take, or one it lacks
            raise ValueError(f"{name}: {error}") from error
    return built
