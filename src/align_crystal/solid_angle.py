"""Solid angle of rectangular detector pixels seen from the sample.

Same idea as `calculate_rectangle_solid_angle` in md_norm's reduction/utils.py (exact solid angle
of a flat rectangle facing the sample, with the pixel normal chosen by the detector geometry),
but with the Van Oosterom-Strackee triangle formula in plain numpy.
"""

import numpy as np


def pixel_normal(position, geometry="cylinder"):
    """Direction the pixel faces: horizontal radial for a cylinder (banana) detector, radial
    for a sphere. `position` is (N, 3), relative to the sample."""
    position = np.asarray(position, float)
    if geometry == "cylinder":
        return position * np.array([1.0, 0.0, 1.0])
    if geometry == "sphere":
        return position.copy()
    raise ValueError(f"Detector geometry {geometry!r} is not recognised (cylinder or sphere).")


def _triangle(a, b, c):
    """Solid angle of the spherical triangle spanned by the vectors a, b, c (Van Oosterom)."""
    num = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    ab, bc, ca = (np.einsum("ij,ij->i", u, v) for u, v in ((a, b), (b, c), (c, a)))
    na, nb, nc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
    return 2 * np.arctan2(num, na * nb * nc + ab * nc + bc * na + ca * nb)


def rectangle_solid_angle(position, width, height, geometry="cylinder"):
    """Solid angle [sr] of flat rectangular pixels as seen from the origin (the sample).

    position: (N, 3) pixel centres relative to the sample; width, height: pixel size (scalar or
    (N,)), width along the horizontal tangent and height along the third axis of the pixel frame.
    """
    position = np.atleast_2d(np.asarray(position, float))
    normal = pixel_normal(position, geometry)
    horiz = np.stack([normal[:, 2], np.zeros(len(normal)), -normal[:, 0]], axis=1)
    horiz /= np.linalg.norm(horiz, axis=1, keepdims=True)
    vert = np.cross(normal, horiz)
    vert /= np.linalg.norm(vert, axis=1, keepdims=True)

    hw = horiz * (np.asarray(width, float) / 2).reshape(-1, 1)
    hh = vert * (np.asarray(height, float) / 2).reshape(-1, 1)
    s1, s2, s3, s4 = (position - hw + hh, position + hw + hh, position + hw - hh, position - hw - hh)
    return _triangle(s1, s2, s3) + _triangle(s1, s3, s4)  # rectangle = two triangles
