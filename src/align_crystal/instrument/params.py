"""The parameters of an instrument: param, Params and InstrParam.

param: a field of a control-parameters dataclass, with its unit and comment in its metadata (what
io/ writes next to its value). Every instrument's `params_class` is made of them.

Params: the control parameters of the diffractometer (`ei` and the goniometer angles), what you
set on it. DEFAULT_PARAMS is the default, shared (frozen).

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
    """A field of `Params`: its default, with its `unit` and `comment` in its metadata."""
    return field(default=default, metadata={"unit": unit, "comment": comment})


@dataclass(frozen=True)
class Params:
    """The control parameters of the diffractometer: what you set on it. Frozen: change them with
    `SingleCrystalDiffractometer.update_params`. Each field's `unit` and `comment` are in its
    metadata."""

    ei: float = param(14.0, "meV", "incident energy")
    omega: float = param(0.0, "deg", "goniometer rotation about +Y")
    chi: float = param(0.0, "deg", "goniometer rotation about -Z")
    phi: float = param(0.0, "deg", "goniometer rotation about +X")


DEFAULT_PARAMS = Params()  # frozen, so one shared default is safe
