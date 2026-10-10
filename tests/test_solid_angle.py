import numpy as np
import pytest

from align_crystal.reduction.solid_angle import rectangle_solid_angle


def test_cube_face_is_one_sixth_of_sphere():
    # unit square at distance 0.5 along x: one face of a cube seen from its centre
    omega = rectangle_solid_angle([[0.5, 0.0, 0.0]], 1.0, 1.0, geometry="sphere")
    assert omega[0] == pytest.approx(4 * np.pi / 6)


def test_small_pixel_is_area_over_distance_squared():
    omega = rectangle_solid_angle([[0.0, 0.0, 2.0]], 1e-3, 2e-3, geometry="cylinder")
    assert omega[0] == pytest.approx(1e-3 * 2e-3 / 4, rel=1e-6)


def test_cylinder_strip_matches_analytic_area():
    # tile a strip of a cylinder (R = 1, height h, angle dphi) with pixels
    R, h, dphi = 1.0, 0.5, np.radians(120)
    nt, ny = 1200, 50
    theta = -dphi / 2 + (np.arange(nt) + 0.5) * dphi / nt
    y = -h / 2 + (np.arange(ny) + 0.5) * h / ny
    t, yy = np.meshgrid(theta, y)
    pos = np.stack([R * np.sin(t).ravel(), yy.ravel(), R * np.cos(t).ravel()], axis=1)
    omega = rectangle_solid_angle(pos, R * dphi / nt, h / ny)
    assert omega.sum() == pytest.approx(dphi * h / np.hypot(R, h / 2), rel=1e-5)
