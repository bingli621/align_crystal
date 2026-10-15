"""The parameters of an instrument: DesignParam and ControlParam.

DesignParam: the parameters of an instrument, as one complete nested dict: what a parameters file
holds, and the only thing read from or written to one. `name`; `controls`, the control parameters
the instrument declares (see below); and one section per component name, in the order of the instrument,
with its `component` (the McStas component name, e.g. "Slit"), its parameters, and last where it sits: `at`,
`rotated` and `relative`. Nothing is merged in from defaults. Where a value is null, the component
derives it itself (the components never see the `DesignParam`). Where the dict comes from (a YAML
file, code, ...) is not the entities' business.

ControlParam: the control parameters, the McStas instrument parameters, which a run sets. The
components are general: the file of an instrument declares its controls in `controls` (each with
its start value, unit and comment; a null value must be set by every run), and a component value
that a control gives is the control's name instead of a number, as in McStas (`energy_meV:
energy_meV`, `rotated: [0, omega, 0]`). `SingleCrystalDiffractometer.control_param` gives those of a
run.

(Simulation parameters, how McStas runs, belong to the McStas layer, not here.)
"""

import copy
from dataclasses import dataclass, replace


class DesignParam:
    """The parameters of an instrument, in memory (the dict is copied)."""

    def __init__(self, data):
        self.data = copy.deepcopy(data)

    def __getitem__(self, key):
        return self.data[key]

    def make(self, component_class, name):
        """The component `name` of `component_class`, made from its section (without its
        `component`)."""
        section = {k: v for k, v in self.data[name].items() if k != "component"}
        try:
            return component_class(**section)
        except TypeError as error:  # a missing or unknown parameter
            raise ValueError(f"Bad parameters for {name!r}: {error}") from None

    def make_components(self, classes: dict) -> dict:
        """The components, keyed by name, in the order of their sections (every key but `name`
        and `controls`); each is the class its section's `component` (the component name) names:
        `classes` maps a component name (e.g. "Slit") to its class. Raises on a section that is not one or has no known
        `component`."""
        components = {}
        for name, section in self.data.items():
            if name in ("name", "controls"):
                continue
            if not isinstance(section, dict):
                raise ValueError(f"Unknown config key: {name} (not a section)")
            component_name = section.get("component")
            if component_name is None:
                raise ValueError(f"No component in the section of {name!r}")
            if component_name not in classes:
                raise ValueError(f"Unknown component {component_name!r} for {name!r}")
            components[name] = self.make(classes[component_name], name)
        return components

    def control_param(self) -> "ControlParam":
        """The control parameters the `controls` section declares (none if there is none)."""
        return ControlParam.from_dict(self.data.get("controls") or {})


@dataclass(frozen=True)
class Control:
    """One control parameter: its start value (None = not set yet: every run sets it), unit and
    comment."""

    value: object
    unit: str = ""
    comment: str = ""


@dataclass(frozen=True)
class ControlParam:
    """The control parameters of an instrument or of one run: each McStas instrument parameter by
    name, with its value (None = not set yet: every run sets it), unit and comment."""

    values: dict
    units: dict
    comments: dict

    @classmethod
    def from_dict(cls, data: dict):
        """The control parameters of a `controls` section: name -> {value, unit, comment}. `value`
        is required (null: every run sets it); `unit` and `comment` are optional."""
        for name, entry in data.items():
            if not isinstance(entry, dict) or "value" not in entry:
                raise ValueError(f"controls.{name} needs a value (null: every run sets it)")
            for key in set(entry) - {"value", "unit", "comment"}:
                raise ValueError(f"Unknown config key: controls.{name}.{key}")
        return cls(
            {name: e["value"] for name, e in data.items()},
            {name: e.get("unit", "") for name, e in data.items()},
            {name: e.get("comment", "") for name, e in data.items()},
        )

    @classmethod
    def from_controls(cls, **controls: Control):
        """The control parameters made of one `Control` each, by McStas name, in order."""
        return cls(
            {name: c.value for name, c in controls.items()},
            {name: c.unit for name, c in controls.items()},
            {name: c.comment for name, c in controls.items()},
        )

    def to_dict(self) -> dict:
        """The `controls` section `from_dict` takes."""
        return {
            name: {"value": v, "unit": self.units[name], "comment": self.comments[name]}
            for name, v in self.values.items()
        }

    def __getitem__(self, name):
        return self.values[name]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def replace(self, **values):
        """A copy with `values` (McStas name -> value) in place of the calculated ones. Raises on
        a name that is not a control parameter."""
        unknown = set(values) - set(self.values)
        if unknown:
            raise ValueError(f"Unknown control parameter(s): {', '.join(sorted(unknown))}")
        return replace(self, values={**self.values, **values})

    def complete(self):
        """This, after checking that every value is set: raises on the ones still None."""
        unset = [name for name, value in self.values.items() if value is None]
        if unset:
            raise ValueError(f"Control parameter(s) not set: {', '.join(unset)}")
        return self
