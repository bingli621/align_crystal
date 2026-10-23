"""Solid angle of rectangular detector pixels seen from the sample.

The idea is that of ``calculate_rectangle_solid_angle`` in md_norm's reduction/utils.py: the
exact solid angle of a flat rectangle facing the sample, with the pixel normal chosen by the
detector geometry. Here it uses the Van Oosterom-Strackee triangle formula in plain numpy.
"""

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

Geometry = Literal["cylinder", "sphere"]


def pixel_normal(position: ArrayLike, geometry: Geometry = "cylinder") -> np.ndarray:
    """Return the direction each pixel faces.

    Parameters
    ----------
    position:
        (N, 3) pixel centres relative to the sample.
    geometry:
        ``"cylinder"`` (banana detector): horizontal radial. Anything else, e.g. ``"sphere"``:
        radial.

    Returns
    -------
    :
        (N, 3) normals, not normalized.
    """
    position = np.asarray(position, float)
    if geometry == "cylinder":
        return position * np.array([1.0, 0.0, 1.0])
    return position.copy()


def _triangle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Compute the solid angle of the spherical triangles spanned by a, b, c (Van Oosterom)."""
    num = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    ab, bc, ca = (np.einsum("ij,ij->i", u, v) for u, v in ((a, b), (b, c), (c, a)))
    na, nb, nc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
    return 2 * np.arctan2(num, na * nb * nc + ab * nc + bc * na + ca * nb)


def rectangle_solid_angle(
    position: ArrayLike,
    width: ArrayLike,
    height: ArrayLike,
    geometry: Geometry = "cylinder",
) -> np.ndarray:
    """Compute the solid angle of flat rectangular pixels seen from the origin (the sample).

    Parameters
    ----------
    position:
        (N, 3) pixel centres relative to the sample.
    width:
        Pixel width along the horizontal tangent, a scalar or (N,).
    height:
        Pixel height along the third axis of the pixel frame, a scalar or (N,).
    geometry:
        Detector geometry, which sets the pixel normal; see :func:`pixel_normal`.

    Returns
    -------
    :
        (N,) solid angles in sr.
    """
    position = np.atleast_2d(np.asarray(position, float))
    normal = pixel_normal(position, geometry)
    horiz = np.stack([normal[:, 2], np.zeros(len(normal)), -normal[:, 0]], axis=1)
    horiz /= np.linalg.norm(horiz, axis=1, keepdims=True)
    vert = np.cross(normal, horiz)
    vert /= np.linalg.norm(vert, axis=1, keepdims=True)

    hw = horiz * (np.asarray(width, float) / 2).reshape(-1, 1)
    hh = vert * (np.asarray(height, float) / 2).reshape(-1, 1)
    s1, s2, s3, s4 = (
        position - hw + hh,
        position + hw + hh,
        position + hw - hh,
        position - hw - hh,
    )
    return _triangle(s1, s2, s3) + _triangle(s1, s3, s4)  # rectangle = two triangles
