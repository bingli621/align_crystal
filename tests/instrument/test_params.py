import pytest

from align_crystal.instrument import InstrParam, complete_values, with_values


def test_with_values_replaces_values_and_rejects_unknown_names():
    params = [InstrParam("omega", 0.0, "deg")]
    assert with_values(params, omega=30)[0].value == 30 and params[0].value == 0.0  # a copy
    with pytest.raises(ValueError, match="Unknown instrument parameter.*omgea"):
        with_values(params, omgea=30)


def test_complete_values_raises_on_a_parameter_that_is_not_set():
    params = [InstrParam("e"), InstrParam("omega", 0.0)]
    with pytest.raises(ValueError, match="not set: e$"):
        complete_values(params)
    assert complete_values(with_values(params, e=14)) == {"e": 14, "omega": 0.0}
