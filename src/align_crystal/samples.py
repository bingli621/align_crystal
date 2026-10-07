"""Single-crystal sample definitions with their orientation in the lab frame.

Lab frame (McStas): z along the beam, y up, x to the left of the beam.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Sample:
    """A single crystal; a*, b*, c* are its reciprocal-lattice vectors in the lab frame
    (1/angstrom, incl. 2pi) when all goniometer angles are zero."""

    reflections: str
    astar: tuple
    bstar: tuple
    cstar: tuple
    mosaic: float  # arc minutes (Gaussian RMS)


def reciprocal_basis(a, b, c, alpha, beta, gamma):
    """Columns are a*, b*, c* (incl. 2pi) in a crystal Cartesian frame with a along x, c* along z."""
    al, be, ga = np.radians([alpha, beta, gamma])
    va = np.array([a, 0, 0])
    vb = np.array([b * np.cos(ga), b * np.sin(ga), 0])
    cx = c * np.cos(be)
    cy = c * (np.cos(al) - np.cos(be) * np.cos(ga)) / np.sin(ga)
    vc = np.array([cx, cy, np.sqrt(c**2 - cx**2 - cy**2)])
    return 2 * np.pi * np.linalg.inv(np.array([va, vb, vc]))  # columns: a*, b*, c*


def oriented_sample(cell, reflections, along_beam, in_plane, mosaic=5.0):
    """Orient a crystal: reciprocal vector `along_beam` (hkl) || +z, `in_plane` (hkl) in the
    horizontal (x-z) plane towards +x (left of the beam)."""
    B = reciprocal_basis(*cell)
    z = B @ np.asarray(along_beam, float)
    x = B @ np.asarray(in_plane, float)
    z /= np.linalg.norm(z)
    x -= z * (x @ z)  # component perpendicular to the beam
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.array([x, y, z])  # crystal Cartesian -> lab
    astar, bstar, cstar = (tuple(R @ B[:, i]) for i in range(3))
    return Sample(str(reflections), astar, bstar, cstar, mosaic)


def aluminium(mosaic=5.0):
    """fcc Al, cubic axes along the lab axes."""
    return oriented_sample(
        (4.0495,) * 3 + (90,) * 3, "Al.lau", (0, 0, 1), (1, 0, 0), mosaic
    )


def la2ni7(mosaic=30.0):
    """La2Ni7 (P6_3/mmc): (001) along the beam, (1.357, 1, 0) in the horizontal plane to the left."""
    return oriented_sample(
        (5.0556, 5.0556, 24.5980, 90, 90, 120),
        DATA_DIR / "La2Ni7.cif",
        (0, 0, 1),
        (1.357, 1, 0),
        mosaic,
    )
