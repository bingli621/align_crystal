"""A generic instrument: a set of components, each with a placement.

Pure entities: no file, YAML or McStas knowledge. An Instrument is created from components
(`from_params`), from the nested dict of its parameters (`from_dict`), or from a file (`from_file`,
which is given the function that reads it), and gives that dict back (`to_dict`). Reading and
writing files is the business of the outer layer (yaml_io.py). mcstas/builder.py builds the McStas
instrument from an Instrument.
"""

from dataclasses import asdict, dataclass, fields

from .components import COMPONENTS, Component
from .params import Param

PLACEMENT = (
    "at",
    "rotated",
    "relative",
)  # the fields of a component that say where it sits


@dataclass(kw_only=True)
class Instrument:
    """All the components of an instrument, keyed by role, in the order they are built (each one
    knows where it sits). A component is also reachable as an attribute: `inst.source` is
    `inst.components["source"]`.

    The constructor takes the components as a dict; `from_params` as keyword arguments. A component derives its null values in its own `__post_init__`; a kind of instrument fills in the
    rest in its own.
    """

    name: str
    components: dict[str, Component]

    def __post_init__(self):
        """Raise if a value that is not optional is still null, i.e. could not be derived. A kind of
        instrument fills in what its components cannot know alone before calling this."""
        for role, c in self.components.items():
            for f in fields(c):
                if getattr(c, f.name) is None and f.name not in c.OPTIONAL:
                    raise ValueError(
                        f"Config value {role}.{f.name} is unresolved (null)"
                    )

    def __getattr__(self, role):
        try:
            return self.__dict__["components"][role]
        except KeyError:
            raise AttributeError(role) from None

    @classmethod
    def from_params(cls, name: str, /, **components: Component):
        """The instrument `name` of `components`, given as keyword arguments in the order of the
        instrument: each keyword is the role of its component (the one that a `relative` refers to).
        A component without a `name` gets its role as its name."""
        for role, c in components.items():
            c.name = c.name or role
        return cls(name=name, components=components)

    @classmethod
    def from_dict(cls, data: dict):
        """The instrument of the complete nested dict `data` (see `Param`): it says everything,
        including which components there are and in which order. Missing and unknown keys raise a
        ValueError."""
        param = Param(data)
        return cls(name=param["name"], components=param.make_components(COMPONENTS))

    @classmethod
    def from_file(cls, file, loader):
        """The instrument of the parameters file `file`, read with `loader`: a function from a path
        to the nested dict that `from_dict` takes (e.g. `yaml_io.yaml_loader`). The entities know no
        file format, so the loader is always given."""
        return cls.from_dict(loader(file))

    def to_dict(self):
        """The nested dict `from_dict` takes; unset optional values (a `name`, an arm's `angle`) are left out."""
        sections, placements = {}, {}
        for role, c in self.components.items():
            values = asdict(c)
            placements[role] = {k: values.pop(k) for k in PLACEMENT}
            sections[role] = {k: v for k, v in values.items() if v is not None}
        return {
            "name": self.name,
            "components": {
                role: type(c).__name__ for role, c in self.components.items()
            },
            **sections,
            "placements": placements,
        }
