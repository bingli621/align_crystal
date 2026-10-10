"""Domain model of the diffractometer: one dataclass per component.

Pure entities, no file, YAML or McStas knowledge (see config_yaml.py to load them and
mcstas/builder.py to build the McStas instrument from them). The dataclasses have no defaults of
their own. Every value left as null is calculated in `__post_init__` (a component derives what
depends only on itself, `DiffractometerConfig` what spans components), so a config is always
fully resolved.
"""

import math
from dataclasses import dataclass, fields
from typing import ClassVar


@dataclass(kw_only=True)
class Component:
    """One piece of the instrument. Its role is its key in the config; `name` optionally gives it
    a different instance name (default: the role)."""

    component_name: str  # kind of component, e.g. "Slit"
    name: str | None = None
    OPTIONAL: ClassVar[tuple] = ("name",)  # fields that may stay None


@dataclass(kw_only=True)
class Source(Component):
    energy_meV: float
    wavelength: float | None  # angstrom, monochromatic; None = derive from energy_meV
    radius: float  # m
    dist: float | None  # source -> focus plane, m; None = sample_pos distance
    flux: float

    def __post_init__(self):
        if self.wavelength is None:
            self.wavelength = math.sqrt(81.80421 / self.energy_meV)  # lambda[A]=sqrt(81.804/E[meV])


@dataclass(kw_only=True)
class Slit(Component):
    size: float  # opening and source focus (x and y), m


@dataclass(kw_only=True)
class GonioArm(Component):
    angle: float  # deg, initial value of the rotation about this arm's axis


@dataclass(kw_only=True)
class Crystal(Component):
    size: float  # cube edge, m
    order: int  # 1 = single scattering only


@dataclass(kw_only=True)
class Detector(Component):
    radius: float  # m
    height: float  # m
    two_theta_range: list  # deg, signed: negative = right of the beam
    n_theta: int
    n_y: int


@dataclass(kw_only=True)
class Placement:
    """Where a component sits: `at` (m) and `rotated` (deg, numbers or parameter names), both
    relative to the component with role `relative` (None = absolute)."""

    at: list
    rotated: list | None
    relative: str | None
    OPTIONAL: ClassVar[tuple] = ("rotated", "relative")


@dataclass(kw_only=True)
class DiffractometerConfig:
    name: str  # instrument name
    origin: Component
    source: Source
    slit1: Slit
    incident_monitor: Component
    sample_pos: Component
    gonio_omega: GonioArm
    gonio_chi: GonioArm
    gonio_phi: GonioArm
    crystal: Crystal
    detector: Detector
    placements: dict  # role -> Placement

    def __post_init__(self):
        if self.source.dist is None:
            self.source.dist = self.placements["sample_pos"].at[2]
        _check_resolved(self)  # raise if a null could not be derived


def _check_resolved(obj, path=""):
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, dict):  # placements
            for k, v in value.items():
                _check_resolved(v, f"{path}{f.name}.{k}.")
        elif hasattr(value, "__dataclass_fields__"):
            _check_resolved(value, f"{path}{f.name}.")
        elif value is None and f.name not in getattr(obj, "OPTIONAL", ()):
            raise ValueError(f"Config value {path}{f.name} is unresolved (null)")
