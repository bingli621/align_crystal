import numpy as np
import pytest

from align_crystal.reduction import goniometer_matrix


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
