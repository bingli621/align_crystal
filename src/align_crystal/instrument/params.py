"""The parameters of an instrument: InstrParam.

InstrParam: one instrument parameter, which McStas takes and a run may set; an instrument has a list
of them (each with its value, unit and comment), which the diffractometer calculates from its params.
The components are general: a component value that one gives is the parameter's name
instead of a number, as in McStas (`rotated: [0, "omega", 0]`).
`SingleCrystalDiffractometer.instrument_param` gives those of a run.

(The design parameters are the components' own values; how they are stored in a file is the io
layer's business, and simulation parameters, how McStas runs, belong to the McStas layer.)
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class InstrParam:
    """One instrument parameter: its McStas name, value, unit and comment."""

    name: str
    value: object = None
    unit: str = ""
    comment: str = ""


def with_values(params: list[InstrParam], **values) -> list[InstrParam]:
    """A copy of `params` with `values` (McStas name -> value) in place of theirs."""
    return [replace(p, value=values[p.name]) if p.name in values else p for p in params]
