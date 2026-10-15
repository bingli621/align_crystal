"""The parameters of an instrument: InstrParam and CtrlParam.

InstrParam: one instrument parameter, which McStas takes and a run sets; an instrument has a list of
them (each with its value, unit and comment; a value None must be set by every run, or is
calculated). The components are general: a component value that one gives is the parameter's name
instead of a number, as in McStas (`rotated: [0, "omega", 0]`).
`SingleCrystalDiffractometer.instrument_param` gives those of a run.

CtrlParam: one control parameter, given when the instrument is made, e.g. the sample and the incident
energy: `SingleCrystalDiffractometer([CtrlParam("crystal", la2ni7(...)), CtrlParam("ei", 14, "meV")])`.

(The design parameters are the components' own values; how they are stored in a file is the io
layer's business, and simulation parameters, how McStas runs, belong to the McStas layer.)
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CtrlParam:
    """One control parameter, given when the instrument is made: its name, value, unit and comment
    (e.g. `CtrlParam("ei", 14, "meV")`, `CtrlParam("crystal", la2ni7(...))`)."""

    name: str
    value: object
    unit: str = ""
    comment: str = ""


@dataclass(frozen=True)
class InstrParam:
    """One instrument parameter: its McStas name, value (None = not set yet: every run sets it, or
    it is calculated), unit and comment."""

    name: str
    value: object = None
    unit: str = ""
    comment: str = ""


def with_values(params: list[InstrParam], **values) -> list[InstrParam]:
    """A copy of `params` with `values` (McStas name -> value) in place of theirs. Raises on a name
    that is not one of them."""
    unknown = set(values) - {p.name for p in params}
    if unknown:
        raise ValueError(f"Unknown instrument parameter(s): {', '.join(sorted(unknown))}")
    return [replace(p, value=values[p.name]) if p.name in values else p for p in params]


def complete_values(params: list[InstrParam]) -> dict:
    """The values of `params` by name, after checking that every one is set: raises on the ones
    still None."""
    unset = [p.name for p in params if p.value is None]
    if unset:
        raise ValueError(f"Instrument parameter(s) not set: {', '.join(unset)}")
    return {p.name: p.value for p in params}
