"""The single-crystal sample and its orientation in the lab frame.

Lab frame (McStas): z along the beam, y up, x to the left of the beam. Ready-made crystals are in
samples/.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from .base import Component

if TYPE_CHECKING:
    from mcstas_to_sqe.core.base import Instrument

# the CIF files of the ready-made samples (mcstas_to_sqe/samples/; only the folder, not imported):
# a crystal's `reflections` names one relative to it
CIF_DIR = Path(__file__).resolve().parents[2] / "samples"


@dataclass(kw_only=True, repr=False)  # repr: Component's
class Single_crystal(Component):
    """A single-crystal cube, as McStas ``Single_crystal``.

    With all goniometer angles at zero, the crystal is oriented so that the reciprocal vector
    ``along_beam`` points along the beam (+z) and ``in_plane`` lies in the horizontal x-z plane,
    towards +x (left of the beam). Ready-made crystals are in samples/ (``aluminum``,
    ``la2ni7``).

    Placement (``at``, ``rotated``, ``relative``) is as in :class:`.Component`.

    Parameters
    ----------
    lattice_params:
        a, b, c in Å, then alpha, beta, gamma in deg.
    along_beam:
        hkl of the reciprocal vector along the beam.
    in_plane:
        hkl of the reciprocal vector in the horizontal plane, towards +x.
    reflections:
        A McStas reflection list (e.g. ``"Al.lau"``), or a CIF file relative to samples/.
    xwidth, yheight, zdepth:
        Size in m.
    order:
        Maximum scattering order. 1 means single scattering only, which is much faster.
    mosaic:
        Mosaic spread in arc minutes (Gaussian RMS).
    recip_cell:
        Must be 1: McStas then takes ``astar``, ``bstar``, ``cstar``, the only parametrization
        computed here.
    """

    lattice_params: list[float]
    along_beam: list[float]
    in_plane: list[float]
    reflections: str
    xwidth: float = 0.005
    yheight: float = 0.005
    zdepth: float = 0.005
    order: int = 1
    mosaic: float = 5.0
    recip_cell: int = 1

    def mcstas_parameters(self, inst: "Instrument") -> dict[str, Any]:
        """Return the McStas parameters, with the reciprocal vectors in the lab frame.

        Parameters
        ----------
        inst:
            The instrument the crystal belongs to.

        Returns
        -------
        :
            The fields, plus ``ax`` ... ``cz`` (the reciprocal vectors). ``reflections`` is
            given as a full path if it names a CIF file in samples/, else unchanged.

        Raises
        ------
        ValueError
            If ``recip_cell`` is not 1.
        """
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
    def astar(self) -> list[float]:
        """Reciprocal vector a* in the lab frame, 1/Å (including 2π)."""
        return self.reciprocal_axes()[0]

    @property
    def bstar(self) -> list[float]:
        """Reciprocal vector b* in the lab frame, 1/Å (including 2π)."""
        return self.reciprocal_axes()[1]

    @property
    def cstar(self) -> list[float]:
        """Reciprocal vector c* in the lab frame, 1/Å (including 2π)."""
        return self.reciprocal_axes()[2]

    def reciprocal_axes(self) -> list[list[float]]:
        """Compute the reciprocal vectors in the lab frame.

        They are computed on every call, so they follow changes of the lattice or orientation.

        Returns
        -------
        :
            ``[astar, bstar, cstar]``, each ``[x, y, z]`` in 1/Å (including 2π).
        """
        B = self.reciprocal_basis()
        z = B @ np.asarray(self.along_beam, float)
        x = B @ np.asarray(self.in_plane, float)
        z /= np.linalg.norm(z)
        x_perp = x - z * (x @ z)  # component perpendicular to the beam
        x = x_perp / np.linalg.norm(x_perp)
        R = np.array([x, np.cross(z, x), z])  # crystal Cartesian -> lab
        return [(R @ B[:, i]).tolist() for i in range(3)]

    def reciprocal_basis(self) -> np.ndarray:
        """Compute the reciprocal basis of ``lattice_params`` in a crystal Cartesian frame.

        The frame has a along x and c* along z.

        Returns
        -------
        :
            (3, 3) matrix whose columns are a*, b*, c* in 1/Å (including 2π).
        """
        a, b, c, alpha, beta, gamma = self.lattice_params
        al, be, ga = np.radians([alpha, beta, gamma])
        va = np.array([a, 0, 0])
        vb = np.array([b * np.cos(ga), b * np.sin(ga), 0])
        cx = c * np.cos(be)
        cy = c * (np.cos(al) - np.cos(be) * np.cos(ga)) / np.sin(ga)
        vc = np.array([cx, cy, np.sqrt(c**2 - cx**2 - cy**2)])
        return 2 * np.pi * np.linalg.inv(np.array([va, vb, vc]))  # columns: a*, b*, c*
