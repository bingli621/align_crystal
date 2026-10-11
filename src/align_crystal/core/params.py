"""Param: all the parameters of an instrument, as one complete nested dict.

`name`, `components` (the kind of each role, in order), one section per role with its
parameters, and `placements` with the `at`, `rotated` and `relative` of each. Nothing is merged in
from defaults. Where a value is null, the component derives it itself (the components never see
the `Param`). Where the dict comes from (a YAML file, code, ...) is not the entities' business.
"""

import copy


class Param:
    """All the parameters of an instrument, in memory (the dict is copied)."""

    def __init__(self, data):
        self.data = copy.deepcopy(data)

    def __getitem__(self, key):
        return self.data[key]

    def make(self, kind, role):
        """The component `kind` of `role`, made from its section and its placement. Its `name` is
        the role unless the section gives one."""
        section = {**self.data[role], **self.data["placements"][role]}
        section["name"] = section.get("name") or role
        try:
            return kind(**section)
        except TypeError as error:  # a missing or unknown parameter
            raise ValueError(f"Bad parameters for {role!r}: {error}") from None

    def make_components(self, kinds: dict) -> dict:
        """The components of `components`, in order, keyed by role: `kinds` maps the name of a
        kind (e.g. "Slit") to its class. Raises on an unknown kind and on sections or placements
        that belong to no component."""
        components = {}
        for role, kind in self.data["components"].items():
            if kind not in kinds:
                raise ValueError(f"Unknown component {kind!r} for {role!r}")
            components[role] = self.make(kinds[kind], role)
        for key in set(self.data) - {"name", "components", "placements", *components}:
            raise ValueError(f"Unknown config key: {key}")
        for key in set(self.data["placements"]) - set(components):
            raise ValueError(f"Unknown config key: placements.{key}")
        return components
