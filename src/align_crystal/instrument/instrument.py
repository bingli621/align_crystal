"""A generic instrument: a set of components, each with a placement.

Pure entities, no file, YAML or McStas knowledge (see file_io/loader.py to load them and
mcstas/builder.py to build the McStas instrument from them). A kind of instrument subclasses
`Instrument` and builds its components, in order, in `from_dict` (see diffractometer.py).
"""

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import ClassVar

from align_crystal.instrument.components import Component

PLACEMENT = ("at", "rotated", "relative")  # the fields of a component that say where it sits


@dataclass(kw_only=True)
class Instrument:
    """All the components of an instrument, keyed by role, in the order they are built (each one
    knows where it sits). A component is also reachable as an attribute: `inst.source` is
    `inst.components["source"]`.

    A subclass sets the class attribute `PARAMS_FILE` (YAML with the default value of every
    parameter) and implements `from_dict`. Nulls that depend on several components are derived in
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
