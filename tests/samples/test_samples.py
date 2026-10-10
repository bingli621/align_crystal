import numpy as np
import pytest

from align_crystal.samples import aluminium, la2ni7


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


def test_aluminium_uses_the_mcstas_reflection_list():
    assert aluminium().reflections == "Al.lau"
