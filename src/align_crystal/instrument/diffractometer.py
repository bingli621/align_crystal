"""The single-crystal diffractometer: its components in beam order, and its defaults.

source -> slit -> incident monitor -> goniometer (three nested arms) + crystal -> detector.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from align_crystal.instrument.components import (
    Arm,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from align_crystal.instrument.instrument import Instrument


@dataclass(kw_only=True)
class Diffractometer(Instrument):
    PARAMS_FILE: ClassVar = Path(__file__).parent / "params.yaml"

    @classmethod
    def from_dict(cls, data):
        """The components in the order of the beam: the roles are the keys of `data`."""

        def make(kind, role):
            return kind(**data[role], **data["placements"][role])

        return cls(
            name=data["name"],
            components={
                "origin": make(Progress_bar, "origin"),
                "source": make(Source_simple, "source"),
                "slit1": make(Slit, "slit1"),
                "incident_monitor": make(Monitor, "incident_monitor"),
                "sample_pos": make(Arm, "sample_pos"),
                "gonio_omega": make(Arm, "gonio_omega"),
                "gonio_chi": make(Arm, "gonio_chi"),
                "gonio_phi": make(Arm, "gonio_phi"),
                "crystal": make(Single_crystal, "crystal"),
                "detector": make(Monitor_nD, "detector"),
            },
        )

    def __post_init__(self):
        """The source focuses on the sample: its distance is the sample position along the beam."""
        if self.source.dist is None:
            self.source.dist = self.sample_pos.at[2]
        super().__post_init__()
