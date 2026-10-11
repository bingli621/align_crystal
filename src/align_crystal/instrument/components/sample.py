"""The sample."""

from dataclasses import dataclass

from .misc import Component


@dataclass(kw_only=True)
class Single_crystal(Component):
    size: float  # cube edge, m
    order: int  # 1 = single scattering only
