"""What every sample has in common: the `Sample` and how to orient a crystal in the lab frame.

Lab frame (McStas): z along the beam, y up, x to the left of the beam.
The individual samples live in their own folders (aluminium/, la2ni7/, ...).
"""

from dataclasses import dataclass

import numpy as np


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
