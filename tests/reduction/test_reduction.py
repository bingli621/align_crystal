import numpy as np
import pytest

from align_crystal.reduction import goniometer_matrix, run_wavelength, wavelength


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


def test_wavelength_of_the_energy():
    assert wavelength(14).value == pytest.approx(2.417262, abs=1e-5)
    assert wavelength(14).unit == "angstrom"


def test_the_wavelength_of_a_scan_point_is_given_or_stored():
    assert run_wavelength({"wavelength": 2.0}).value == 2.0  # stored by the McStas run
    assert run_wavelength({"wavelength": 2.0}, wavelength(14)).value == pytest.approx(
        2.417262, abs=1e-5
    )
