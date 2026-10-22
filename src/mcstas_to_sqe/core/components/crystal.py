"""The single crystal, and how to orient one in the lab frame.

Lab frame (McStas): z along the beam, y up, x to the left of the beam. Ready-made crystals are in
samples/.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .base import Component

# the CIF files of the ready-made samples (mcstas_to_sqe/samples/; only the folder, not imported):
# a crystal's `reflections` names one relative to it
CIF_DIR = Path(__file__).resolve().parents[2] / "samples"


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Single_crystal(Component):
    """A cube of a single crystal of `lattice_params`, oriented so that the reciprocal vector
    `along_beam` (hkl) is along the beam (+z) and `in_plane` (hkl) is in the horizontal (x-z)
    plane towards +x (left of the beam), when all goniometer angles are zero. Ready-made crystals:
    samples/ (`aluminum`, `la2ni7`).

    `astar`, `bstar`, `cstar`, its reciprocal-lattice vectors in the lab frame (1/angstrom, incl.
    2pi), are computed from these when used (so they follow a change of them); they are not
    parameters of their own.
    """

    lattice_params: list  # a, b, c (angstrom), alpha, beta, gamma (deg)
    along_beam: list  # hkl along the beam
    in_plane: list  # hkl in the horizontal plane, towards +x
    reflections: str  # a McStas list (Al.lau), or a CIF file relative to samples/
    xwidth: float = 0.005  # m: a cube by default
    yheight: float = 0.005  # m
    zdepth: float = 0.005  # m
    order: int = 1  # 1 = single scattering only (no multiple scattering): much faster
    mosaic: float = 5.0  # arc minutes (Gaussian RMS)
    recip_cell: int = 1  # 1: McStas takes astar, bstar, cstar (the only one it computes)

    def mcstas_parameters(self, inst):
        """Its fields, with its reciprocal vectors in the lab frame (so recip_cell must be 1); its
        reflections a CIF file of samples/ (as a full path), else as given (a McStas
        list)."""
        if self.recip_cell != 1:
            raise ValueError(f"{self.name}: recip_cell {self.recip_cell}: only 1 is computed")
        cif = CIF_DIR / self.reflections
        vectors = {
            f"{axis}{x}": value
            for axis, vector in zip("abc", self.reciprocal_axes())
            for x, value in zip("xyz", vector)
        }
        reflections = str(cif) if cif.is_file() else self.reflections
        return super().mcstas_parameters(inst) | {"reflections": reflections, **vectors}

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
