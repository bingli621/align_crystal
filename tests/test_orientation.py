import numpy as np
import pytest

from align_crystal.io import goniometer_matrix
from align_crystal.samples import la2ni7


def test_la2ni7_orientation():
    s = la2ni7()
    a, b, c = (np.array(v) for v in (s.astar, s.bstar, s.cstar))
    # (001) along +z, the beam
    assert c[:2] == pytest.approx(0, abs=1e-9) and c[2] > 0
    # (1.357, 1, 0) in the horizontal plane (y = 0), towards +x
    q = 1.357 * a + b
    assert q[1] == pytest.approx(0, abs=1e-9) and q[0] > 0
    # right-handed lattice
    assert np.dot(np.cross(a, b), c) > 0


def test_goniometer_matrix():
    assert goniometer_matrix(0, 0, 0) == pytest.approx(np.eye(3))
    # omega: right-handed rotation about +Y
    assert goniometer_matrix(90, 0, 0) @ [0, 0, 1] == pytest.approx([1, 0, 0])
    # chi: rotation about -Z
    assert goniometer_matrix(0, 90, 0) @ [1, 0, 0] == pytest.approx([0, -1, 0])
    # phi: rotation about +X
    assert goniometer_matrix(0, 0, 90) @ [0, 1, 0] == pytest.approx([0, 0, 1])
    R = goniometer_matrix(10, 20, 30)
    assert R @ R.T == pytest.approx(np.eye(3))
