import numpy as np
import pytest

from align_crystal.reduction import centre_of_mass


def _cloud(rng):
    # two scan points, 300 points each, around (1, 2, 3)
    q = rng.normal([1.0, 2.0, 3.0], [0.05, 0.1, 0.02], size=(600, 3))
    w = rng.uniform(0.5, 1.5, 600)
    scan = np.repeat([0, 1], 300)
    return q, w, 0.04 * w**2, scan, np.array([100.0, 120.0]), np.array([2.0, 3.0])


def test_centre_of_mass_value():
    q, w, var, scan, mon, mon_err = _cloud(np.random.default_rng(0))
    qc, cov, W, W_err = centre_of_mass(q, w, var, scan, mon, mon_err)
    assert qc == pytest.approx(w @ q / w.sum())
    assert W == pytest.approx(w.sum())
    assert np.all(np.linalg.eigvalsh(cov) > 0)


def test_error_propagation_matches_resampling():
    rng = np.random.default_rng(1)
    q, w, var, scan, mon, mon_err = _cloud(rng)
    qc, cov, W, W_err = centre_of_mass(q, w, var, scan, mon, mon_err)

    # resample the weights: Gaussian noise on each weight, and on each monitor reading (w ~ 1/I0)
    centres, totals = [], []
    for _ in range(4000):
        i0 = mon + rng.normal(0, mon_err)
        w_new = (w + rng.normal(0, np.sqrt(var))) * (mon / i0)[scan]
        c, _, tot, _ = centre_of_mass(q, w_new, var, scan, mon, mon_err)
        centres.append(c)
        totals.append(tot)
    assert np.std(centres, axis=0) == pytest.approx(np.sqrt(np.diag(cov)), rel=0.1)
    assert np.std(totals) == pytest.approx(W_err, rel=0.1)
