"""A generic instrument: a set of components, each with a placement.

Pure entities, no file, YAML or McStas knowledge. Files are reached through `ConfigFormat`, an
abstraction defined here and implemented by the outer layer (file_io/loader.py has the YAML one):
`from_file` and `to_file` take the format as an argument, so this module never imports an
implementation. mcstas/builder.py builds the McStas instrument from an Instrument. A kind of
instrument subclasses `Instrument` and builds its components, in order, in `from_dict` (see
diffractometer/diffractometer.py).
"""

import copy
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import ClassVar, Protocol

from .components import Component

PLACEMENT = ("at", "rotated", "relative")  # the fields of a component that say where it sits


class ConfigFormat(Protocol):
    """How a nested dict is stored in a file (YAML, JSON, ...). The outer layer implements it."""

    def read(self, path) -> dict: ...

    def write(self, data: dict, path) -> None: ...


def _merge(base, over, roles, path=""):
    """Return `base` with the values of `over` applied, recursively. Unknown keys raise.
    The section of a component (a role) may also set `name`, its McStas instance name."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        if key not in base and not (key == "name" and path.rstrip(".") in roles):
            raise ValueError(f"Unknown config key: {path}{key}")
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            out[key] = _merge(base[key], value, roles, f"{path}{key}.")
        else:
            out[key] = value
    return out


@dataclass(kw_only=True)
class Instrument:
    """All the components of an instrument, keyed by role, in the order they are built (each one
    knows where it sits). A component is also reachable as an attribute: `inst.source` is
    `inst.components["source"]`.

    A subclass sets the class attribute `PARAMS_FILE` (a file with the default value of every
    parameter, in the format used to read it) and implements `from_dict`. Nulls that depend on several components are derived in
    the subclass's `__post_init__`, which must end with `super().__post_init__()`.
    """

    name: str
    components: dict[str, Component]

    PARAMS_FILE: ClassVar[Path | None] = None

    def __post_init__(self):
        """Raise if a value that is not optional is still null, i.e. could not be derived."""
        for role, c in self.components.items():
            for f in fields(c):
                if getattr(c, f.name) is None and f.name not in c.OPTIONAL:
                    raise ValueError(f"Config value {role}.{f.name} is unresolved (null)")

    def __getattr__(self, role):
        try:
            return self.__dict__["components"][role]
        except KeyError:
            raise AttributeError(role) from None

    @classmethod
    def from_dict(cls, data):
        """Build the instrument from a complete nested dict: `name`, one section per component
        with its parameters, and `placements` with the `at`, `rotated` and `relative` of each.
        A subclass creates its components here, one after the other."""
        raise NotImplementedError

    @classmethod
    def from_overrides(cls, overrides: dict, fmt: ConfigFormat):
        """The instrument with the default values of its kind (read from `PARAMS_FILE` with `fmt`)
        and the nested dict `overrides` applied on top. Keys that are not in the defaults raise."""
        defaults = fmt.read(cls.PARAMS_FILE)
        roles = defaults["placements"]  # one entry per component
        return cls.from_dict(_merge(defaults, overrides, roles))

    @classmethod
    def from_file(cls, path, fmt: ConfigFormat):
        """The instrument with the default values of its kind and the file `path` on top; only
        the values the file lists are changed."""
        return cls.from_overrides(fmt.read(path), fmt)

    def to_file(self, path, fmt: ConfigFormat):
        """Write the instrument to `path`, in the same layout as the default values."""
        fmt.write(self.to_dict(), path)

    def to_dict(self):
        """The inverse of `from_dict`. Unset optional values of a component (its `name`, a static
        arm's `angle`) are left out."""
        placed = {role: asdict(c) for role, c in self.components.items()}
        return {
            "name": self.name,
            **{
                role: {k: v for k, v in d.items() if k not in PLACEMENT and v is not None}
                for role, d in placed.items()
            },
            "placements": {role: {k: d[k] for k in PLACEMENT} for role, d in placed.items()},
        }
