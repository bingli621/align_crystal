"""The sample: a single crystal, and how to orient one in the lab frame.

Lab frame (McStas): z along the beam, y up, x to the left of the beam.

Ready-made crystals: each function gives a `Single_crystal` of its own lattice and orientation;
`params` are the crystal's other parameters, or ones to change, e.g.
`la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")`. A CIF file is in instrument/cif/ (a plain
folder), and `reflections` names it relative to `CIF_DIR`, so a saved parameters file is
portable.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .misc import Component

CIF_DIR = Path(__file__).parents[1] / "cif"  # the CIF files of the ready-made crystals


@dataclass(kw_only=True)
class Single_crystal(Component):
    """A cube of a single crystal of `lattice_params`, oriented so that the reciprocal vector
    `along_beam` (hkl) is along the beam (+z) and `in_plane` (hkl) is in the horizontal (x-z)
    plane towards +x (left of the beam), when all goniometer angles are zero. Ready-made crystals:
    `aluminum`, `la2ni7` below.

    `astar`, `bstar`, `cstar`, its reciprocal-lattice vectors in the lab frame (1/angstrom, incl.
    2pi), are computed from these when used (so they follow a change of them); they are not
    parameters of their own.
    """

    lattice_params: list  # a, b, c (angstrom), alpha, beta, gamma (deg)
    along_beam: list  # hkl along the beam
    in_plane: list  # hkl in the horizontal plane, towards +x
    reflections: str  # a McStas list (Al.lau), or a CIF file relative to instrument/cif/
    xwidth: float = 0.005  # m: a cube by default
    yheight: float = 0.005  # m
    zdepth: float = 0.005  # m
    order: int = 1  # 1 = single scattering only (no multiple scattering): much faster
    mosaic: float = 5.0  # arc minutes (Gaussian RMS)

    @property
    def astar(self) -> list:
        return self.reciprocal_axes()[0]

    @property
    def bstar(self) -> list:
        return self.reciprocal_axes()[1]

    @property
    def cstar(self) -> list:
        return self.reciprocal_axes()[2]

    def reciprocal_axes(self) -> list:
        """`astar`, `bstar`, `cstar` (plain floats)."""
        B = self.reciprocal_basis()
        z = B @ np.asarray(self.along_beam, float)
        x = B @ np.asarray(self.in_plane, float)
        z /= np.linalg.norm(z)
        x_perp = x - z * (x @ z)  # component perpendicular to the beam
        x = x_perp / np.linalg.norm(x_perp)
        R = np.array([x, np.cross(z, x), z])  # crystal Cartesian -> lab
        return [(R @ B[:, i]).tolist() for i in range(3)]

    def reciprocal_basis(self):
        """Columns are a*, b*, c* (incl. 2pi) of `lattice_params` in a crystal Cartesian frame with
        a along x, c* along z."""
        a, b, c, alpha, beta, gamma = self.lattice_params
        al, be, ga = np.radians([alpha, beta, gamma])
        va = np.array([a, 0, 0])
        vb = np.array([b * np.cos(ga), b * np.sin(ga), 0])
        cx = c * np.cos(be)
        cy = c * (np.cos(al) - np.cos(be) * np.cos(ga)) / np.sin(ga)
        vc = np.array([cx, cy, np.sqrt(c**2 - cx**2 - cy**2)])
        return 2 * np.pi * np.linalg.inv(np.array([va, vb, vc]))  # columns: a*, b*, c*


def aluminum(**params) -> Single_crystal:
    """fcc Al, the McStas built-in reflection list Al.lau; cubic axes along the lab axes."""
    return Single_crystal(
        **{
            "lattice_params": [4.0495, 4.0495, 4.0495, 90.0, 90.0, 90.0],
            "along_beam": [0, 0, 1],
            "in_plane": [1, 0, 0],
            "reflections": "Al.lau",
            **params,
        }
    )


def la2ni7(**params) -> Single_crystal:
    """La2Ni7 (P6_3/mmc), structure from La2Ni7.cif (COD 1523044): (001) along the beam,
    (1.357, 1, 0) in the horizontal plane to the left."""
    return Single_crystal(
        **{
            "lattice_params": [5.0556, 5.0556, 24.5980, 90.0, 90.0, 120.0],
            "along_beam": [0, 0, 1],
            "in_plane": [1.357, 1, 0],
            "reflections": "La2Ni7.cif",
            "mosaic": 30.0,
            **params,
        }
    )
