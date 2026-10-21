"""The parameters of any instrument: param and InstrParam.

param: a field of a control-parameters dataclass, with its unit and comment in its metadata (what
io/ writes next to its value). Every instrument's `params_class` is made of them (the
diffractometer's: `Params` in instruments/diffractometer/scd.py).

InstrParam: one McStas instrument parameter, which McStas takes and a run may set; an instrument's
`instr_params` is the list of them (each with its value, unit and comment), calculated from its
params. The components are general: a component value that one gives is the parameter's name (or
an expression of them) instead of a number, as in McStas (`rotated: [0, "omega", 0]`).

(The design parameters are the components' own values; how they are stored in a file is the io
layer's business, and simulation parameters, how McStas runs, belong to the McStas layer.)
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InstrParam:
    """One instrument parameter: its McStas name, value, unit and comment."""

    name: str
    value: object = None
    unit: str = ""
    comment: str = ""


def param(default: float, unit: str, comment: str):
    """A field of a `params_class`: its default, with its `unit` and `comment` in its metadata."""
    return field(default=default, metadata={"unit": unit, "comment": comment})
