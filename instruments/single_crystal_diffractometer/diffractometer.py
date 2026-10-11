"""The single-crystal diffractometer: source -> slit -> incident monitor -> goniometer (three
nested arms) + crystal -> detector.

It is an `Instrument` that knows its own default parameters and one rule of its own: the source
focuses on a component (the sample), and its focus distance follows from where that is. Two ways to
create it: `from_file` and `from_dict` (inherited) takes a complete dict of parameters, with the layout of
params.yaml, which names the components in beam order; and `from_parameters` makes the same
components directly, in code. `from_file` reads a file into one, with a loader (YAML by default).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from align_crystal.core import (
    Arm,
    Instrument,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from align_crystal.yaml_io import yaml_loader


@dataclass(kw_only=True)
class SingleCrystalDiffractometer(Instrument):
    # the complete default parameters file
    PARAMS_FILE: ClassVar = Path(__file__).parent / "params.yaml"

    def __post_init__(self):
        """The source focuses on a component (`focus_on`, the sample): unless its `dist` is given,
        it is the z of that component, which is placed relative to the source."""
        source = self.components["source"]
        if source.dist is None:
            if source.focus_on not in self.components:
                raise ValueError(
                    f"The source focuses on {source.focus_on!r}, which is not a component"
                )
            source.dist = self.components[source.focus_on].at[2]
        super().__post_init__()

    @classmethod
    def from_file(cls, file=None, loader=yaml_loader):
        """The diffractometer of the parameters file `file` (default: its own `PARAMS_FILE`), read
        with `loader`: a function from a path to the nested dict that `from_dict` takes (YAML by
        default)."""
        return super().from_file(file or cls.PARAMS_FILE, loader)

    @classmethod
    def from_parameters(cls):
        """The diffractometer with the default parameters, its components made directly here, one
        by one, and given to the instrument in the order of the beam (the same values as the
        parameters file). Lengths in m, angles in deg. A value left None is calculated: by the
        component itself, or by the instrument from the other components (the source focus
        distance)."""
        origin = Progress_bar(at=[0, 0, 0])
        source = Source_simple(
            energy_meV=14,
            wavelength=None,  # angstrom, monochromatic: derived from energy_meV
            radius=0.03,
            focus_on="sample_pos",  # the component the source focuses on
            dist=None,  # source -> focus plane: derived by the instrument from focus_on
            flux=1.0e10,
            at=[0, 0, 0],
            relative="origin",
        )
        slit1 = Slit(size=0.01, at=[0, 0, 1.0], relative="source")  # opening = source focus
        # integrated incident intensity, 10 cm before the sample; the neutrons carry on
        incident_monitor = Monitor(at=[0, 0, 1.9], relative="source")
        # the beam hits the goniometer centre; it can be dumped here
        sample_pos = Arm(at=[0, 0, 2.0], relative="source")
        # goniometer arms, outermost first; `angle` is the initial value of the McStas parameter
        # named after the arm without "gonio_" (omega, chi, phi), so it can be scanned
        gonio_omega = Arm(
            angle=0.0, at=[0, 0, 0], rotated=[0, "omega", 0], relative="sample_pos"
        )  # about +Y
        gonio_chi = Arm(
            angle=0.0, at=[0, 0, 0], rotated=[0, 0, "-chi"], relative="gonio_omega"
        )  # about -Z
        gonio_phi = Arm(
            angle=0.0, at=[0, 0, 0], rotated=["phi", 0, 0], relative="gonio_chi"
        )  # about +X
        crystal = Single_crystal(
            size=0.005,  # cube edge
            order=1,  # single scattering only (no multiple scattering): much faster
            at=[0, 0, 0],
            relative="gonio_phi",
        )
        # cylindrical ("banana") detector around the vertical axis through the sample
        detector = Monitor_nD(
            radius=1.0,
            height=0.5,
            two_theta_range=[-125.0, -5.0],  # signed: negative = right of the beam
            n_theta=1200,
            n_y=50,
            at=[0, 0, 0],
            relative="sample_pos",
        )

        return cls.from_params(
            "align_crystal_diffractometer",  # in the order of the beam; each keyword is the role
            origin=origin,
            source=source,
            slit1=slit1,
            incident_monitor=incident_monitor,
            sample_pos=sample_pos,
            gonio_omega=gonio_omega,
            gonio_chi=gonio_chi,
            gonio_phi=gonio_phi,
            crystal=crystal,
            detector=detector,
        )
