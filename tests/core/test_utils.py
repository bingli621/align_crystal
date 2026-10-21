import math

import pytest

from align_crystal.core.utils import evaluate

PARAMS = {"omega": 30.0, "chi": 5.0, "x": 0.5}  # floats, as the params are


@pytest.mark.parametrize(
    "entry, value",
    [
        (1.5, 1.5),
        ("omega", 30),
        ("-chi", -5),
        ("2.0*omega + chi", 65.0),
        ("(omega - chi) / 5.0", 5.0),
        ("omega / 4", 7.5),  # a float in the division: the same in C
        ("atan2(1, 1)*RAD2DEG", 45.0),
        ("sin(x)", math.sin(0.5)),
        ("PI", math.pi),
    ],
)
def test_an_expression_is_computed_as_mcstas_would(entry, value):
    assert evaluate(entry, PARAMS) == pytest.approx(value)


@pytest.mark.parametrize(
    "entry, match",
    [
        ("psi", "'psi' is not"),  # not an instrument parameter
        ("omega ** 2", "omega \\*\\* 2"),  # not C
        ("omega ^ 2", "omega \\^ 2"),  # XOR in C
        ("1/2", "rounding down"),  # 0 in C
        ("__import__('os')", "__import__"),  # no code is run
        ("omega.real", "omega.real"),
        ("2 *", "not an expression"),
    ],
)
def test_anything_else_raises(entry, match):
    with pytest.raises(ValueError, match=match):
        evaluate(entry, PARAMS)
